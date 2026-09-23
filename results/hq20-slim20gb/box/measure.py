#!/usr/bin/env python3
import argparse, json, statistics, subprocess, sys, time, urllib.request

BASE = "http://127.0.0.1:18020"
MODEL = "qwen3.8-27b"
SUFFIX = "Write a careful technical explanation of PCIe Gen3 x16. Use complete sentences."
FILLER = "Explain quantum error correction in complete sentences. "
TOK_PER_REPEAT = 8.05
OVERHEAD = 50


def hygiene():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"]).decode().strip().split(",")
        return {"gpu_util": float(out[0]), "mem_used": float(out[1]), "mem_total": float(out[2]),
                "temp": float(out[3]), "power": float(out[4])}
    except Exception as e:
        return {"error": str(e)}


def build_prompt(target):
    if target <= 0:
        return SUFFIX
    repeats = max(1, int((target - OVERHEAD) / TOK_PER_REPEAT))
    return FILLER * repeats + "\n\n" + SUFFIX


def metrics_counters():
    try:
        raw = urllib.request.urlopen(BASE + "/metrics", timeout=30).read().decode()
    except Exception:
        return {}, ""
    keep = {}
    rawkeep = []
    for line in raw.splitlines():
        low = line.lower()
        if "spec" in low and not line.startswith("#"):
            rawkeep.append(line)
            parts = line.rsplit(" ", 1)
            if len(parts) == 2:
                try:
                    keep[parts[0]] = float(parts[1])
                except ValueError:
                    pass
    return keep, "\n".join(rawkeep)


def stream_chat(prompt, max_tokens):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    ttft = None
    last = {}
    text = []
    with urllib.request.urlopen(req, timeout=3600) as resp:
        for line in resp:
            line = line.decode().strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            d = json.loads(payload)
            if d.get("choices") and d["choices"][0].get("delta", {}).get("content"):
                if ttft is None:
                    ttft = time.time()
                text.append(d["choices"][0]["delta"]["content"])
            if d.get("usage"):
                last = d
    t_end = time.time()
    usage = last.get("usage", {}) if last else {}
    choice = (last.get("choices") or [{}])[0] if last else {}
    return {
        "ttft": (ttft - t0) if ttft else None,
        "elapsed": t_end - t0,
        "end_minus_ttft": (t_end - ttft) if ttft else None,
        "usage": usage,
        "finish_reason": choice.get("finish_reason"),
        "text_chars": sum(len(t) for t in text),
        "raw_final": last,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fill", type=int, default=0)
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--max-tokens", type=int, default=600)
    p.add_argument("--out", default="")
    p.add_argument("--label", default="hq20")
    args = p.parse_args()
    prompt = build_prompt(args.fill)
    lines = []
    hb = hygiene()
    lines.append("HYGIENE_BEFORE " + json.dumps(hb))
    print(lines[-1], flush=True)
    c0, raw0 = metrics_counters()
    warm = stream_chat(prompt, args.max_tokens)
    wct = warm["usage"].get("completion_tokens", 0)
    wdec = (wct - 1) / warm["end_minus_ttft"] if warm["end_minus_ttft"] else 0
    lines.append("warmup_discarded ttft=%.2f decode=%.2f ct=%d pt=%d" % (
        warm["ttft"] or -1, wdec, wct, warm["usage"].get("prompt_tokens", 0)))
    print(lines[-1], flush=True)
    rows = []
    for i in range(args.n):
        c1, _ = metrics_counters()
        r = stream_chat(prompt, args.max_tokens)
        c2, _ = metrics_counters()
        ct = r["usage"].get("completion_tokens", 0)
        pt = r["usage"].get("prompt_tokens", 0)
        dec = (ct - 1) / r["end_minus_ttft"] if r["end_minus_ttft"] else 0
        e2e = ct / r["elapsed"] if r["elapsed"] else 0
        pre = pt / r["ttft"] if r["ttft"] else 0
        dacc = {k: c2[k] - c1.get(k, 0) for k in c2 if k in c1 and c2[k] != c1.get(k)}
        row = {"run": i + 1, "prompt_tokens": pt, "completion_tokens": ct,
               "ttft": r["ttft"], "decode_tok_s": dec, "e2e_tok_s": e2e,
               "prefill_derived_tok_s": pre, "elapsed": r["elapsed"],
               "finish_reason": r["finish_reason"], "spec_metric_delta": dacc,
               "text_chars": r["text_chars"]}
        rows.append(row)
        lines.append(
            "run %d: prompt_tokens=%d completion_tokens=%d ttft=%.2fs elapsed=%.2fs decode=%.2f e2e=%.2f prefill_derived=%.1f finish=%s spec_delta=%s"
            % (i + 1, pt, ct, r["ttft"] or -1, r["elapsed"], dec, e2e, pre, r["finish_reason"], json.dumps(dacc, sort_keys=True)))
        print(lines[-1], flush=True)
    med_dec = statistics.median(r["decode_tok_s"] for r in rows)
    med_e2e = statistics.median(r["e2e_tok_s"] for r in rows)
    med_ttft = statistics.median(r["ttft"] for r in rows if r["ttft"])
    med_pt = statistics.median(r["prompt_tokens"] for r in rows)
    lines.append("median_decode_tok_s=%.2f median_e2e_tok_s=%.2f median_ttft_s=%.2f median_prompt_tokens=%d n=%d dec_runs=%s"
                 % (med_dec, med_e2e, med_ttft, med_pt, args.n, [round(r["decode_tok_s"], 2) for r in rows]))
    print(lines[-1], flush=True)
    if rows:
        lines.append("raw_final=" + json.dumps(rows[-1].get("spec_metric_delta", {}), sort_keys=True))
        lines.append("final_response_keys=" + json.dumps(sorted((rows[-1] or {}).keys())))
    _, raw1 = metrics_counters()
    ha = hygiene()
    lines.append("HYGIENE_AFTER " + json.dumps(ha))
    print(lines[-1], flush=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write("\n".join(lines) + "\n")
            f.write("# spec_metrics_window\n" + raw1 + "\n")
            f.write("# last_raw_final\n" + json.dumps(rows[-1] if rows else {}, default=str) + "\n")
        print("wrote " + args.out, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
