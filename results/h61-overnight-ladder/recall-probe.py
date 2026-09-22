#!/usr/bin/env python3
"""h61 beyond-window recall test. Mandatory on every SWA rung. Runs ON THE BOX.

Plants 4 literals before a long filler that pushes them beyond the SWA window,
then asks for exact recall. SWA hybrid must return 4/4 (globals carry them).
Pure windowed attention hallucinates here. Any miss is a REJECT for the SWA arm.
Uses /v1/chat/completions like the decode harness. Fill sizes are prompt tokens.
"""
import argparse
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8083"
LITERALS = ["XKQ-1138", "MARO VESS", "47291", "CATTLEYA LUMINA"]
FILLER = "Explain quantum error correction in complete sentences. "
TOK_PER_REPEAT = 8.05
OVERHEAD = 120


def build_beyond_window_prompt(fill_tokens):
    head = (
        "The vault code is XKQ-1138. The courier name is MARO VESS. "
        "The port number is 47291. The orchid species is CATTLEYA LUMINA. "
        "Remember these exactly. Now read the following background.\n\n"
    )
    repeats = max(1, int((fill_tokens - OVERHEAD) / TOK_PER_REPEAT))
    tail = (
        "\n\nNow recall exactly: what is the vault code, courier name, "
        "port number, and orchid species? Answer with only those four values."
    )
    return head + FILLER * repeats + tail


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fill", type=int, default=33355)
    p.add_argument("--out", default="")
    args = p.parse_args()
    prompt = build_beyond_window_prompt(args.fill)
    body = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0,
        "stream": False,
        "cache_prompt": False,
        "enable_thinking": False,
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=1800) as resp:
        d = json.loads(resp.read().decode())
    text = ""
    try:
        text = d["choices"][0]["message"]["content"] or ""
    except Exception:
        text = json.dumps(d)[:2000]
    hits = [lit for lit in LITERALS if lit in text]
    ok = len(hits) == 4
    print("fill=%d prompt_chars=%d" % (args.fill, len(prompt)), flush=True)
    print("A: " + text.strip()[:2000], flush=True)
    print("recall=%d/4 hits=%s" % (len(hits), ",".join(hits)), flush=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write("fill=%d\nA: %s\nrecall=%d/4 hits=%s\n" % (
                args.fill, text.strip(), len(hits), ",".join(hits)))
        print("wrote " + args.out, flush=True)
    if not ok:
        print("REJECT: beyond-window recall failed", flush=True)
        return 1
    print("PASS: beyond-window recall 4/4", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
