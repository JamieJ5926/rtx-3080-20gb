#!/usr/bin/env python3
"""Median generate tok/s. Frozen hillclimb harness.

Three runs. 600 new tokens. temperature 0. Empty ctx (new request each run).
Prints one line: median_tok_s=<float> n=3 think=<0|1> model=<name>
"""
import argparse
import json
import statistics
import sys
import urllib.request


def one_run(url, model, think, n_predict):
    body = {
        "model": model,
        "prompt": "Write a careful technical explanation of PCIe Gen3 x16. Use complete sentences.",
        "stream": False,
        "think": think,
        "options": {"num_predict": n_predict, "temperature": 0},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        d = json.loads(resp.read().decode())
    ec = d.get("eval_count") or 0
    ed = d.get("eval_duration") or 0
    if ed <= 0 or ec <= 0:
        raise SystemExit(f"bad timings eval_count={ec} eval_duration={ed}")
    tok_s = ec / (ed / 1e9)
    return {
        "tok_s": tok_s,
        "eval_count": ec,
        "resp_len": len(d.get("response") or ""),
        "think_len": len(d.get("thinking") or ""),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:11434/api/generate")
    p.add_argument("--model", default="qwen3.8:27b")
    p.add_argument("--think", action="store_true")
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--num-predict", type=int, default=600)
    args = p.parse_args()
    rows = [one_run(args.url, args.model, args.think, args.num_predict) for _ in range(args.n)]
    med = statistics.median(r["tok_s"] for r in rows)
    print(
        f"median_tok_s={med:.3f} n={args.n} think={int(args.think)} model={args.model} "
        f"runs={[round(r['tok_s'], 3) for r in rows]} "
        f"resp_len={[r['resp_len'] for r in rows]} think_len={[r['think_len'] for r in rows]}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
