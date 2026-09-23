#!/usr/bin/env python3
import argparse, json, random, string, sys, urllib.request

BASE = "http://127.0.0.1:18020"
FILLER = "Explain quantum error correction in complete sentences. "
TOK_PER_REPEAT = 8.05
OVERHEAD = 120


def make_literals(seed):
    rng = random.Random(seed)
    def tok(n):
        return "".join(rng.choice(string.ascii_uppercase) for _ in range(n))
    code = "%s%d-%s" % (tok(3), rng.randint(1000, 9999), tok(4))
    courier = "%s %s" % (tok(5), tok(6))
    port = str(rng.randint(20000, 65000))
    orchid = "%s %s" % (tok(7), tok(6))
    return [code, courier, port, orchid]


def build_prompt(lits, fill_tokens):
    head = ("The vault code is %s. The courier name is %s. The port number is %s. "
            "The orchid species is %s. Remember these exactly. Now read the following background.\n\n"
            % (lits[0], lits[1], lits[2], lits[3]))
    repeats = max(1, int((fill_tokens - OVERHEAD) / TOK_PER_REPEAT))
    tail = ("\n\nNow recall exactly: what is the vault code, courier name, port number, "
            "and orchid species? Answer with only those four values.")
    return head + FILLER * repeats + tail


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fill", type=int, default=33355)
    p.add_argument("--seed", type=int, default=20260923)
    p.add_argument("--out", default="")
    args = p.parse_args()
    lits = make_literals(args.seed)
    prompt = build_prompt(lits, args.fill)
    body = {
        "model": "qwen3.8-27b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
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
    with urllib.request.urlopen(req, timeout=3600) as resp:
        d = json.loads(resp.read().decode())
    try:
        text = d["choices"][0]["message"]["content"] or ""
    except Exception:
        text = json.dumps(d)[:2000]
    hits = [lit for lit in lits if lit in text]
    ok = len(hits) == 4
    out_lines = [
        "seed=%d fill=%d prompt_chars=%d" % (args.seed, args.fill, len(prompt)),
        "literals=" + json.dumps(lits),
        "A: " + text.strip(),
        "recall=%d/4 hits=%s" % (len(hits), json.dumps(hits)),
        "PASS" if ok else "REJECT",
    ]
    blob = "\n".join(out_lines) + "\n"
    print(blob, flush=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write(blob)
        print("wrote " + args.out, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
