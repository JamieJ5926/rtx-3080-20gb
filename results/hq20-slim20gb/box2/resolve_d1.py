#!/usr/bin/env python3
p = "/home/jamie/vllm-slim-src/vllm/v1/spec_decode/llm_base_proposer.py"
lines = open(p).read().split("\n")
out, ours, theirs = [], [], []
mode, blocks = None, 0
for line in lines:
    if line.startswith("<<<<<<<"):
        mode, ours, theirs = "ours", [], []
        blocks += 1
        continue
    if line.startswith("=======") and mode == "ours":
        mode = "theirs"
        continue
    if line.startswith(">>>>>>>") and mode == "theirs":
        out.extend(theirs if any("getattr" in l for l in theirs) else ours)
        mode = None
        continue
    (ours if mode == "ours" else theirs if mode == "theirs" else out).append(line)
assert mode is None and blocks >= 1, "expected conflict blocks, got %d" % blocks
s = "\n".join(out)
assert s.count('getattr(self.speculative_config.draft_load_config, "load_format", "auto")') == blocks
assert "self.speculative_config.draft_load_config.load_format" not in s
open(p, "w").write(s)
print("resolved", blocks, "block(s)")
