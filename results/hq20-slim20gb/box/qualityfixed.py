#!/usr/bin/env python3
import argparse, json, sys, urllib.request

BASE = "http://127.0.0.1:18020"
PROMPT = (
    "The vault code is XKQ-1138. The courier name is MARO VESS. "
    "The port number is 47291. The orchid species is CATTLEYA LUMINA. "
    "Explain quantum error correction in complete sentences. "
    "The vault code is XKQ-1138. The courier name is MARO VESS. "
    "The port number is 47291. The orchid species is CATTLEYA LUMINA. "
    "Now recall exactly: what is the vault code, courier name, port number, "
    "and orchid species? Answer with only those four values."
)
LITERALS = ["XKQ-1138", "MARO VESS", "47291", "CATTLEYA LUMINA"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="")
    args = p.parse_args()
    body = {
        "model": "qwen3.8-27b",
        "messages": [{"role": "user", "content": "Q: " + PROMPT}],
        "max_tokens": 600,
        "temperature": 0,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        d = json.loads(resp.read().decode())
    try:
        text = d["choices"][0]["message"]["content"] or ""
    except Exception:
        text = json.dumps(d)[:2000]
    hits = [lit for lit in LITERALS if lit in text]
    ok = len(hits) == 4 and len(text.strip()) > 0
    lines = ["Q: " + PROMPT, "", "A: " + text.strip(),
             "recall=%d/4 hits=%s" % (len(hits), json.dumps(hits)),
             "finish=%s" % d.get("choices", [{}])[0].get("finish_reason"),
             "PASS" if ok else "REJECT"]
    blob = "\n".join(lines) + "\n"
    print(blob, flush=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write(blob)
        print("wrote " + args.out, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
