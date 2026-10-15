"""Frozen harness for the long-context agentic climb. One command emits every metric as one JSON line.

Workload, built to look like a coding agent session on a real repo:
  1. Cold prefill: a 32K-token context of real source files (CORPUS_DIR) with five planted facts. Measures prefill
     tok/s, time to first token, decode tok/s right after it, and recall (x/5).
  2. Agent turns: six follow-up turns on that same conversation. Each adds about 3K tokens of new source and asks
     for one tool call (read_file with a path that exists in the new text). Measures per-turn prefill of the new
     tokens, time to first token, decode tok/s, and tool-call validity (right tool, JSON args, path present).
  3. Short chat: three 100-token answers on a fresh short prompt, as a regression check on the plain-decode speed.

Every request runs at temperature 0. Usage: CORPUS_DIR=dir python3 agentic_bench.py BASE_URL MODEL LABEL
"""
import json
import os
import pathlib
import random
import statistics
import sys
import time
import urllib.request

BASE, MODEL, LABEL = sys.argv[1], sys.argv[2], sys.argv[3]
CTX_TOKENS, TURNS, TURN_TOKENS = 32000, 6, 3000
TOOLS = [{"type": "function", "function": {
    "name": "read_file", "description": "Read a file from the repository",
    "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}]


def chunks():
    root = pathlib.Path(os.environ["CORPUS_DIR"])
    files = sorted(p for p in root.rglob("*") if p.suffix in {".c", ".cpp", ".h", ".hpp", ".py", ".md"} and p.is_file())
    for p in files:
        rel = str(p.relative_to(root))
        for para in p.read_text(encoding="utf-8", errors="replace").split("\n\n"):
            if para.strip():
                yield rel, f"// file {rel}\n{para.strip()}"


SOURCE = chunks()


def take(n_tokens):
    out, paths, approx = [], [], 0
    while approx < n_tokens:
        rel, c = next(SOURCE)
        out.append(c)
        paths.append(rel)
        approx += len(c) // 4 + 1
    return out, paths


def post(messages, max_tokens, tools=None):
    body = {"model": MODEL, "temperature": 0, "max_tokens": max_tokens, "messages": messages,
            "chat_template_kwargs": {"enable_thinking": False}}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        resp = json.load(r)
    return resp, time.time() - t0


def timing(resp, wall):
    t = resp.get("timings", {})
    return {"prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n"), "prefill_tok_s": t.get("prompt_per_second"),
            "ttft_s": round(t.get("prompt_ms", 0) / 1000, 2), "decode_tok_s": t.get("predicted_per_second"),
            "decode_n": t.get("predicted_n"), "wall_s": round(wall, 1),
            "draft": f"{t.get('draft_n_accepted')}/{t.get('draft_n')}"}


rng = random.Random(7)
paras, _ = take(CTX_TOKENS)
facts = []
for i, depth in enumerate([0.05, 0.30, 0.50, 0.70, 0.95]):
    code = f"{rng.choice('BCDFGHJKLMNPQRSTVWXZ')}{rng.randint(1000, 9999)}-K{i}"
    facts.append(code)
    paras.insert(int(len(paras) * depth), f"// NOTE: release key {i + 1} is {code}. Keep it exactly.")
context = "\n\n".join(paras)

msgs = [{"role": "system", "content": f"You are a coding agent working in a repository. Session {LABEL}."},
        {"role": "user", "content": context + "\n\nList release keys 1 to 5, one per line as 'key N: VALUE'. "
                                              "Nothing else."}]
resp, wall = post(msgs, 120)
answer = resp["choices"][0]["message"].get("content") or ""
cold = timing(resp, wall) | {"recall": f"{sum(c in answer for c in facts)}/5"}
msgs.append({"role": "assistant", "content": answer})

turns = []
for t in range(TURNS):
    new, paths = take(TURN_TOKENS)
    target = paths[len(paths) // 2]
    msgs.append({"role": "user", "content": "\n\n".join(new) +
                 f"\n\nCall read_file on {target} so we can look at it in full. Use the tool, no prose."})
    resp, wall = post(msgs, 200, TOOLS)
    m = resp["choices"][0]["message"]
    calls = m.get("tool_calls") or []
    ok = False
    if len(calls) == 1 and calls[0]["function"]["name"] == "read_file":
        try:
            ok = json.loads(calls[0]["function"]["arguments"]).get("path") == target
        except (ValueError, AttributeError):
            ok = False
    turns.append(timing(resp, wall) | {"tool_ok": ok})
    msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": calls} if calls else
                {"role": "assistant", "content": m.get("content") or ""})
    if calls:
        msgs.append({"role": "tool", "tool_call_id": calls[0].get("id", "x"), "content": "(file contents elided)"})

chat = []
for q in ["Explain what a mutex is in four sentences.", "Explain binary search in four sentences.",
          "Explain what a closure is in four sentences."]:
    resp, wall = post([{"role": "user", "content": q}], 100)
    chat.append(timing(resp, wall)["decode_tok_s"])


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


print(json.dumps({
    "label": LABEL,
    "cold_prefill_tok_s": cold["prefill_tok_s"], "cold_ttft_s": cold["ttft_s"], "cold_decode_tok_s": cold["decode_tok_s"],
    "recall": cold["recall"],
    "turn_prefill_tok_s_med": med(t["prefill_tok_s"] for t in turns),
    "turn_ttft_s_med": med(t["ttft_s"] for t in turns),
    "turn_decode_tok_s_med": med(t["decode_tok_s"] for t in turns),
    "tool_ok": f"{sum(t['tool_ok'] for t in turns)}/{TURNS}",
    "chat_decode_tok_s_med": med(chat),
    "cold": cold, "turns": turns, "chat": chat}), flush=True)
