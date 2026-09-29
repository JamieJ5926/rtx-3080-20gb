#!/usr/bin/env python3
"""cache-probe.py — does the server reuse the prompt prefix across identical turns?
Compares first-call vs second-call elapsed for chat (no cache flag) and native
/completion (explicit cache_prompt), at a realistic agent depth."""
import json, sys, time, urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8083
BASE = f"http://127.0.0.1:{PORT}"
FILL = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

BLOCK = "GET /api/v2/items/%d -> 200\n{\"id\":%d,\"owner\":\"team-%d\",\"state\":\"open\",\"notes\":\"staging mirror, sync 5m\",\"bucket\":\"assets-%d\"}\n"
corpus = "".join(BLOCK % (i, i, i % 20, i) for i in range(max(1, FILL // 25)))

def post(path, body, timeout=600):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return round(time.time() - t0, 2), d

chat = {"messages": [{"role": "user", "content": corpus + "\nSummarise the endpoints."}],
        "max_tokens": 120, "temperature": 0}
e1, r1 = post("/v1/chat/completions", chat)
e2, r2 = post("/v1/chat/completions", chat)
pt = (r1.get("usage") or {}).get("prompt_tokens", 0)
print(f"chat: prompt={pt} first={e1}s second={e2}s speedup={round(e1/max(e2,0.01),2)}x")

native = {"prompt": corpus + "\nSummarise the endpoints.", "n_predict": 120,
          "temperature": 0, "cache_prompt": True}
n1, _ = post("/completion", native)
n2, _ = post("/completion", native)
print(f"native(cache_prompt=true): first={n1}s second={n2}s speedup={round(n1/max(n2,0.01),2)}x")

native_off = dict(native, cache_prompt=False)
c1, _ = post("/completion", native_off)
c2, _ = post("/completion", native_off)
print(f"native(cache_prompt=false): first={c1}s second={c2}s speedup={round(c1/max(c2,0.01),2)}x")
