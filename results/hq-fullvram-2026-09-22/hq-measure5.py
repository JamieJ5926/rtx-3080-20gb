import json, urllib.request, time, statistics

BASE = "http://127.0.0.1:18020"
MODEL = "qwen3.8-27b"
PROMPT = "Write a careful technical explanation of PCIe Gen3 x16. Use complete sentences."
OUT = "/home/jamie/hq-trial/measure-5.txt"


def chat(prompt, max_tokens):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
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
    return u.get("completion_tokens", 0), u.get("prompt_tokens", 0), el


lines = []
rs = []
for i in range(3):
    ct, pt, el = chat(PROMPT, 600)
    ts = ct / el if el > 0 else 0
    rs.append(ts)
    lines.append(
        "run %d: completion_tokens=%d prompt_tokens=%d elapsed=%.2fs tok_s=%.2f"
        % (i + 1, ct, pt, el, ts)
    )
    print(lines[-1], flush=True)
med = statistics.median(rs)
lines.append(
    "median_decode_tok_s=%.2f n=3 runs=%s" % (med, [round(x, 2) for x in rs])
)
print(lines[-1], flush=True)

long_prompt = "Explain quantum error correction in complete sentences. " * 1100
ct, pt, el = chat(long_prompt, 8)
lines.append(
    "prefill10k: prompt_tokens=%d completion_tokens=%d elapsed=%.2fs prefill_tok_s=%.1f"
    % (ct and pt, ct, el, pt / el if el > 0 else 0)
)
print(lines[-1], flush=True)

open(OUT, "w").write("\n".join(lines) + "\n")
print("wrote " + OUT, flush=True)
