#!/usr/bin/env bash
# Output-quality checks against the live Flash server. Runs on the Mac; the suite runs on home-pc-1.
#  1. The 10-case quality suite (tool calls/JSON, coding with tests, 16K recall), scored.
#  2. Recall: five planted facts at about 32K, 128K and 230K tokens, in logbook text and in real C++ source.
#  3. Logprob fingerprint: greedy 256-token answers to 6 fixed prompts, saved for a quant-to-quant comparison.
# Usage: bash quality_check.sh LABEL
set -u
L=$1
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/quality/$L
mkdir -p "$OUT"
PC() { ssh -n -o BatchMode=yes -o ConnectTimeout=15 -o ControlMaster=no -o ControlPath=none home-pc-1 "$@"; }

R=/home/jamie/mixed-cluster/runs/serve/quality-$L
PC "rm -rf $R; cd /home/jamie/mixed-cluster/runs/pc-climb && /home/jamie/mixed-cluster/vendor/Strata/.venv/bin/python quality/run_quality.py --base-url http://127.0.0.1:8080 --tokenizer /home/jamie/mixed-cluster/strata-data/packs/iq3s/tokenizer --out $R >/dev/null 2>$R.err; /home/jamie/mixed-cluster/vendor/Strata/.venv/bin/python quality/score_quality.py --help >/dev/null 2>&1; ls $R" >"$OUT/suite-files.txt"
PC "cat $R/scores.json 2>/dev/null || cat $R.err | tail -5" >"$OUT/suite-scores.json"

CORPUS_DIR= python3 "$HERE/recall.py" http://127.0.0.1:18080/v1 qwen3.8-flash-next-iq3_s 32000 128000 230000 >"$OUT/recall-logbook.jsonl" 2>&1
CORPUS_DIR=/Users/jamie/Projects/active/mixed-cluster-wt/strata-upstream/src \
  python3 "$HERE/recall.py" http://127.0.0.1:18080/v1 qwen3.8-flash-next-iq3_s 32000 128000 >"$OUT/recall-code.jsonl" 2>&1

python3 - "$OUT/fingerprint.jsonl" <<'EOF'
import json, sys, urllib.request
prompts = [
    "Write a Python function that merges overlapping intervals. Return only the code.",
    "Explain the difference between a process and a thread in exactly five sentences.",
    "A train leaves at 14:05 and arrives at 17:52. How long is the trip in minutes? Show the working.",
    "Write a JSON object describing a user with fields name, email, roles (a list) and active (a boolean).",
    "Summarise what a B-tree is and why databases use it, in under 120 words.",
    "Write a bash one-liner that counts lines in every .py file under the current directory and prints the total.",
]
with open(sys.argv[1], "w") as f:
    for p in prompts:
        body = {"model": "qwen3.8-flash-next-iq3_s", "temperature": 0, "max_tokens": 256, "logprobs": True,
                "top_logprobs": 5, "messages": [{"role": "user", "content": p}],
                "chat_template_kwargs": {"enable_thinking": False}}
        r = json.load(urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:18080/v1/chat/completions", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}), timeout=600))
        c = r["choices"][0]
        f.write(json.dumps({"prompt": p, "text": c["message"].get("content"), "logprobs": c.get("logprobs")}) + "\n")
EOF

python3 - "$OUT" <<'EOF'
import json, pathlib, sys
o = pathlib.Path(sys.argv[1])
try:
    s = json.loads((o / "suite-scores.json").read_text())
    suite = f"{s['earned']}/{s['total']}"
    misses = [c["id"] for c in s.get("cases", []) if c["earned"] < c["max"]]
except Exception as e:
    suite, misses = f"unreadable ({e})", []
def rec(name):
    rows = []
    for l in (o / name).read_text().splitlines():
        try:
            d = json.loads(l); rows.append(f"{d['prompt_tokens']}:{d['recall']}")
        except ValueError:
            pass
    return rows
fp = [json.loads(l) for l in (o / "fingerprint.jsonl").read_text().splitlines()]
print(json.dumps({"label": o.name, "suite": suite, "suite_misses": misses, "recall_logbook": rec("recall-logbook.jsonl"),
                  "recall_code": rec("recall-code.jsonl"), "fingerprint_has_logprobs": all(x["logprobs"] for x in fp)}))
EOF
