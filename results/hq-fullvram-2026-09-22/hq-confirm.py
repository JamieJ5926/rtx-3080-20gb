import json, urllib.request, time, statistics

BASE = "http://127.0.0.1:8083"
PROMPT = "Write a careful technical explanation of PCIe Gen3 x16. Use complete sentences."
OUT = "/home/jamie/hq-trial/confirm-production.txt"


def chat(max_tokens):
    body = {
        "model": "/home/jamie/models/orcarouter-uncensored-IQ4_XS.gguf",
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
    ch = d["choices"][0]
    msg = ch.get("message", {})
    text = msg.get("content", "")
    u = d.get("usage", {})
    return u.get("completion_tokens", 0), el, d.get("timings", {}), text


lines = []
rs = []
last_timings = {}
for i in range(3):
    ct, el, tm, _ = chat(600)
    ts = ct / el if el > 0 else 0
    rs.append(ts)
    last_timings = tm
    lines.append(
        "run %d: completion_tokens=%d elapsed=%.2fs tok_s=%.2f"
        % (i + 1, ct, el, ts)
    )
    print(lines[-1], flush=True)
med = statistics.median(rs)
lines.append(
    "median_decode_tok_s=%.2f n=3 runs=%s" % (med, [round(x, 2) for x in rs])
)
print(lines[-1], flush=True)
lines.append("timings=" + json.dumps(last_timings))
print(lines[-1], flush=True)
open(OUT, "w").write("\n".join(lines) + "\n")
print("wrote " + OUT, flush=True)
