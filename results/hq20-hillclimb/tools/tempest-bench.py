#!/usr/bin/env python3
"""tempest-bench.py — Tempest-shaped benchmark for any OpenAI-compatible server.

Measures what a bug-bounty agent actually feels: recon-dump prompts at realistic
fill depths, a summarize-and-extract completion, sequential n=5 after warmup,
then a small concurrent burst. Writes JSON + prints a compact summary.

Usage:
  python3 tempest-bench.py --port 18020 --out /path/prefix --depth 8192 20480 --burst 2
"""
import argparse, json, threading, time, urllib.request

RECON_BLOCK = """--- http://recon-host-{i}/api/v2/config/export ---
HTTP/1.1 200 OK
Server: nginx/1.24.0
Content-Type: application/json
X-Request-Id: req-{i}-a91f3c7e
Set-Cookie: sid={sid}; HttpOnly; SameSite=Lax

{{"service":"config-export","version":"2.{minor}.1","endpoints":["/api/v2/users","/api/v2/tokens","/api/v2/files/{i}"],"internal_notes":"staging mirror of prod, sync every 5m","owner_team":"platform-infra","last_deploy":"2026-0{m}-{d}T09:41:07Z"}}
--- response headers from /admin/health (misconfigured) ---
HTTP/1.1 200 OK
X-Backend: worker-{h}
X-Debug-Trace: trace-id={tid}; span=frontend; db=pg-main-replica
Content-Length: 4123

<div id="app" data-config='{{"apiBase":"/api/v2","s3Bucket":"company-assets-{i}","redisHost":"10.0.{a}.{b}:6379"}}'>
  <script>window.__BOOT__ = {{"user":null,"features":["new_billing","export_v2"],"build":"{h}.2.{minor}"}};</script>
  <!-- TODO: remove legacy /internal/migrate.php before Q3 audit -->
</div>
"""

SYSTEM = "You are a recon analyst. Summarize security-relevant findings in 3 terse bullets, then list any endpoints, buckets, or internal hosts you spotted."

def http_chat(port, messages, max_tokens, timeout=180):
    body = json.dumps({"messages": [{"role": "system", "content": SYSTEM}] + messages,
                       "max_tokens": max_tokens, "temperature": 0, "stream": False}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    dt = time.time() - t0
    u = d.get("usage", {})
    return {"pt": u.get("prompt_tokens", 0), "ct": u.get("completion_tokens", 0),
            "elapsed": round(dt, 2), "tok_s": round(u.get("completion_tokens", 0) / dt, 2)}

def build_prompt(port, target):
    """Grow the recon corpus until prompt_tokens >= target. Returns messages."""
    n = 1
    while True:
        corpus = "".join(
            RECON_BLOCK.format(i=j, sid=f"s3ss10n{j:04d}x", minor=j % 9, m=1 + j % 9,
                               d=1 + j % 28, h=j % 250, tid=f"tr-{j:06d}",
                               a=j % 250, b=(j * 7) % 250)
            for j in range(n))
        messages = [{"role": "user", "content": corpus + "\n\nAnalyze the dump above."}]
        r = http_chat(port, messages, 32, timeout=120)
        if r["pt"] >= target or n > 400:
            return messages, r["pt"], n
        n = max(n + 1, int(n * target / max(r["pt"], 1)) + 1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--depth", type=int, nargs="+", default=[8192, 20480])
    ap.add_argument("--burst", type=int, default=2)
    args = ap.parse_args()

    results = {"server": f"http://127.0.0.1:{args.port}", "points": {}}
    for depth in args.depth:
        messages, pt, blocks = build_prompt(args.port, depth)
        print(f"[depth {depth}] built prompt: {pt} prompt tokens, {blocks} recon blocks")
        http_chat(args.port, messages, 64, timeout=120)  # warmup, discarded
        runs = []
        for i in range(5):
            r = http_chat(args.port, messages, 250)
            runs.append(r)
            print(f"  seq run {i+1}: ct={r['ct']} elapsed={r['elapsed']}s decode={r['tok_s']} tok/s")
        seq = [r["tok_s"] for r in runs]
        burst_results, lock = [], threading.Lock()
        def worker():
            r = http_chat(args.port, messages, 250, timeout=180)
            with lock:
                burst_results.append(r)
        rounds = []
        for _ in range(5):
            ts = [threading.Thread(target=worker) for _ in range(args.burst)]
            t0 = time.time()
            [t.start() for t in ts]
            [t.join() for t in ts]
            wall = time.time() - t0
            rounds.append({"wall": round(wall, 2),
                           "toks": sum(r["ct"] for r in burst_results[-args.burst:])})
        agg = round(sum(r["toks"] for r in rounds) / sum(r["wall"] for r in rounds), 2)
        per = sorted(r["tok_s"] for r in burst_results)
        print(f"  burst {args.burst}x: aggregate={agg} tok/s, per-request median={per[len(per)//2]}")
        results["points"][str(depth)] = {
            "prompt_tokens": pt, "seq_decode_tok_s": sorted(seq)[2],
            "seq_all": seq,
            "burst": {"workers": args.burst, "aggregate_tok_s": agg,
                      "per_request_sorted": per,
                      "rounds": rounds}}

    with open(args.out + "-tempest-bench.json", "w") as f:
        json.dump(results, f, indent=1)
    print(json.dumps({k: {"seq": v["seq_decode_tok_s"],
                          "burst_agg": v["burst"]["aggregate_tok_s"]}
                      for k, v in results["points"].items()}))

if __name__ == "__main__":
    main()