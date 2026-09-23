#!/usr/bin/env python3
import json, statistics, sys, time, urllib.request

BASE = "http://127.0.0.1:8083"
PROMPT = "Write a careful technical explanation of PCIe Gen3 x16. Use complete sentences."
MODEL = "/home/jamie/models/orcarouter-uncensored-IQ4_XS.gguf"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jamie/hq20/h76verify.txt"


def chat(max_tokens):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": False,
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as resp:
        d = json.loads(resp.read().decode())
    el = time.time() - t0
    u = d.get("usage", {})
    return u.get("completion_tokens", 0), el, d.get("timings", {})


lines = []
rs = []
last_timings = {}
for i in range(3):
    ct, el, tm = chat(600)
    ts = ct / el if el > 0 else 0
    rs.append(ts)
    last_timings = tm
    lines.append("run %d: completion_tokens=%d elapsed=%.2fs tok_s=%.2f" % (i + 1, ct, el, ts))
    print(lines[-1], flush=True)
med = statistics.median(rs)
lines.append("median_decode_tok_s=%.2f n=3 runs=%s" % (med, [round(x, 2) for x in rs]))
print(lines[-1], flush=True)
lines.append("timings=" + json.dumps(last_timings))
print(lines[-1], flush=True)
engine = last_timings.get("predicted_per_second", 0)
dn = last_timings.get("draft_n", 0)
da = last_timings.get("draft_n_accepted", 0)
ok = 71.0 <= engine <= 77.0 and 350 <= da <= 450 and 500 <= dn <= 650
lines.append("VERIFY %s engine_decode=%.2f draft=%d/%d" % ("PASS" if ok else "FAIL", engine, da, dn))
print(lines[-1], flush=True)
open(OUT, "w").write("\n".join(lines) + "\n")
print("wrote " + OUT, flush=True)
sys.exit(0 if ok else 1)
