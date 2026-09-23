#!/usr/bin/env python3
import argparse, json, sys, urllib.request

BASE = "http://127.0.0.1:18020"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="")
    args = p.parse_args()
    body = {
        "model": "qwen3.8-27b",
        "messages": [{"role": "user", "content": "What is the weather in Copenhagen right now? Use the weather tool."}],
        "tools": [{"type": "function", "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}],
        "tool_choice": "auto",
        "max_tokens": 300,
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
    msg = d.get("choices", [{}])[0].get("message", {})
    calls = msg.get("tool_calls") or []
    lines = ["raw=" + json.dumps(d, default=str)]
    ok = False
    if calls:
        fn = calls[0].get("function", {})
        name = fn.get("name", "")
        try:
            argsj = json.loads(fn.get("arguments", "{}"))
        except Exception:
            argsj = {}
        ok = name == "get_weather" and "copenhagen" in str(argsj.get("city", "")).lower()
        lines.append("tool_call name=%s arguments=%s" % (name, json.dumps(argsj)))
    lines.append("PASS" if ok else "REJECT")
    blob = "\n".join(lines) + "\n"
    print(blob, flush=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write(blob)
        print("wrote " + args.out, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
