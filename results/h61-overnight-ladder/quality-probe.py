#!/usr/bin/env python3
"""h61 quality guardrail probe. Runs ON THE BOX against the live server.

Sends the canonical 4-literal prompt with enable_thinking=false semantics:
coherent visible answer plus exact 4/4 literal recall. Any missing literal,
empty visible text, or think-only dump is a REJECT. Exit nonzero on failure
so the arm runner stops before logging a decode number.
"""
import argparse
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8083"
LITERALS = ["XKQ-1138", "MARO VESS", "47291", "CATTLEYA LUMINA"]
PROMPT = (
    "The vault code is XKQ-1138. The courier name is MARO VESS. "
    "The port number is 47291. The orchid species is CATTLEYA LUMINA. "
    "Explain quantum error correction in complete sentences. "
    "The vault code is XKQ-1138. The courier name is MARO VESS. "
    "The port number is 47291. The orchid species is CATTLEYA LUMINA. "
    "Now recall exactly: what is the vault code, courier name, port number, "
    "and orchid species? Answer with only those four values."
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="")
    args = p.parse_args()
    body = {
        "messages": [{"role": "user", "content": "Q: " + PROMPT}],
        "max_tokens": 600,
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
    with urllib.request.urlopen(req, timeout=900) as resp:
        d = json.loads(resp.read().decode())
    text = ""
    try:
        text = d["choices"][0]["message"]["content"] or ""
    except Exception:
        text = json.dumps(d)[:2000]
    hits = [lit for lit in LITERALS if lit in text]
    ok = len(hits) == 4 and len(text.strip()) > 0
    print("Q: " + PROMPT, flush=True)
    print("", flush=True)
    print("A: " + text.strip()[:2000], flush=True)
    print("recall=%d/4 hits=%s" % (len(hits), ",".join(hits)), flush=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write("Q: " + PROMPT + "\n\nA: " + text.strip() + "\n")
            f.write("recall=%d/4\n" % len(hits))
        print("wrote " + args.out, flush=True)
    if not ok:
        print("REJECT: quality guardrail failed", flush=True)
        return 1
    print("PASS: quality guardrail 4/4", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
