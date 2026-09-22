#!/usr/bin/env python3
"""Frozen h56 ladder harness with Rule 7 weight-residency and VRAM verification.

Protocol (matches h54 baseline shape):
- endpoint: http://127.0.0.1:8083/v1/chat/completions (run ON THE BOX)
- model: /home/jamie/models/orcarouter-uncensored-IQ4_XS.gguf
- 600 tokens, temp 0, cache_prompt false, stream False
- filler prompt: FILLER_SENTENCE repeated + PCIe instruction suffix
- metric: server timings predicted_per_second (decode), prompt_per_second (prefill)
- median of 3 per point
- Rule 7 measurement hygiene: verifies VRAM residency before run; logs desktop & GPU memory.
"""
import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8083"
MODEL = "/home/jamie/models/orcarouter-uncensored-IQ4_XS.gguf"
SUFFIX = "Write a careful technical explanation of PCIe Gen3 x16. Use complete sentences."
FILLER = "Explain quantum error correction in complete sentences. "
TOK_PER_REPEAT = 8.05
OVERHEAD = 50


def check_gpu_hygiene():
    """Rule 7: verify weights resident in VRAM and report desktop/compositor memory."""
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ]
        out = subprocess.check_output(cmd).decode().strip().split(",")
        gpu_util = float(out[0].strip())
        mem_used = float(out[1].strip())
        mem_total = float(out[2].strip())
        temp = float(out[3].strip())
        pwr = float(out[4].strip())
    except Exception as e:
        return {"error": str(e), "mem_used": 0, "resident": False}

    # Find desktop / compositor processes in nvidia-smi
    desktop_mem = 0
    try:
        p_out = subprocess.check_output(["nvidia-smi", "--query-compute-apps=pid,used_memory,process_name", "--format=csv,noheader"]).decode()
        for line in p_out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3 and any(k in parts[2].lower() for k in ("hyprland", "xwayland", "waybar", "sway", "gnome", "kwin", "plasma")):
                val = parts[1].replace("MiB", "").strip()
                if val.isdigit():
                    desktop_mem += int(val)
    except Exception:
        pass

    # Expected compute memory for IQ4_XS: model is ~14.5 GB, context ~3.4 GB. Total > 17500 MiB.
    # If mem_used < 16000 MiB, weights have spilled to host RAM!
    resident = mem_used >= 16000
    return {
        "gpu_util": gpu_util,
        "mem_used": mem_used,
        "mem_total": mem_total,
        "temp": temp,
        "power": pwr,
        "desktop_mem": desktop_mem,
        "resident": resident,
    }


def build_prompt(target):
    if target <= 0:
        return SUFFIX
    repeats = max(1, int((target - OVERHEAD) / TOK_PER_REPEAT))
    return FILLER * repeats + "\n\n" + SUFFIX


def one_run(prompt, max_tokens):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": False,
        "cache_prompt": False,
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as resp:
        d = json.loads(resp.read().decode())
    el = time.time() - t0
    u = d.get("usage", {})
    tm = d.get("timings", {})
    ct = u.get("completion_tokens", 0)
    pt = u.get("prompt_tokens", 0) or tm.get("prompt_n", 0)
    dec = tm.get("predicted_per_second", 0) or (ct / el if el > 0 else 0)
    pre = tm.get("prompt_per_second", 0)
    return {
        "ct": ct,
        "pt": pt,
        "el": el,
        "dec": dec,
        "pre": pre,
        "draft_n": tm.get("draft_n", 0),
        "draft_acc": tm.get("draft_n_accepted", 0),
        "timings": tm,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fill", type=int, default=0)
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--max-tokens", type=int, default=600)
    p.add_argument("--out", default="")
    args = p.parse_args()

    # Rule 7 hygiene check
    hygiene = check_gpu_hygiene()
    print(
        f"HYGIENE: VRAM used={hygiene['mem_used']:.0f}/{hygiene['mem_total']:.0f} MiB "
        f"desktop_mem={hygiene['desktop_mem']} MiB temp={hygiene['temp']:.0f}C "
        f"resident={hygiene['resident']}",
        flush=True,
    )
    if not hygiene["resident"] and hygiene["mem_used"] > 0:
        print("WARNING: VRAM usage is below 16000 MiB! Weights may have spilled to host RAM.", file=sys.stderr)

    prompt = build_prompt(args.fill)
    rows = [one_run(prompt, args.max_tokens) for _ in range(args.n)]
    for i, r in enumerate(rows):
        print(
            "run %d: prompt_tokens=%d completion_tokens=%d elapsed=%.2fs "
            "decode=%.2f prefill=%.1f draft=%s/%s"
            % (
                i + 1, r["pt"], r["ct"], r["el"], r["dec"], r["pre"],
                r["draft_acc"], r["draft_n"],
            ),
            flush=True,
        )
    med_dec = statistics.median(r["dec"] for r in rows)
    med_pre = statistics.median(r["pre"] for r in rows if r["pre"] > 0)
    med_pt = statistics.median(r["pt"] for r in rows)
    print(
        "median_decode_tok_s=%.2f median_prefill_tok_s=%.1f median_prompt_tokens=%.0f n=%d runs=%s"
        % (med_dec, med_pre, med_pt, args.n, [round(r["dec"], 2) for r in rows]),
        flush=True,
    )
    if rows:
        print("timings=" + json.dumps(rows[-1]["timings"]), flush=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write(f"# HYGIENE: used={hygiene['mem_used']} total={hygiene['mem_total']} desktop={hygiene['desktop_mem']} resident={hygiene['resident']}\n")
            for i, r in enumerate(rows):
                f.write(
                    "run %d: prompt_tokens=%d completion_tokens=%d elapsed=%.2fs "
                    "decode=%.2f prefill=%.1f draft=%s/%s\n"
                    % (
                        i + 1, r["pt"], r["ct"], r["el"], r["dec"], r["pre"],
                        r["draft_acc"], r["draft_n"],
                    )
                )
            f.write(
                "median_decode_tok_s=%.2f median_prefill_tok_s=%.1f "
                "median_prompt_tokens=%.0f n=%d runs=%s\n"
                % (med_dec, med_pre, med_pt, args.n, [round(r["dec"], 2) for r in rows])
            )
            f.write("timings=" + json.dumps(rows[-1]["timings"]) + "\n")
        print("wrote " + args.out, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
