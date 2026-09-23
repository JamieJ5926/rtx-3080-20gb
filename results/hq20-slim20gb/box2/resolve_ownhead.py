#!/usr/bin/env python3
GET = '            and getattr(self.speculative_config.draft_load_config, "load_format", "auto") in ("auto", "hf", "safetensors")'
OLD = '            and self.speculative_config.draft_load_config.load_format in ("auto", "hf", "safetensors")'
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
        print("=== CONFLICT BLOCK %d ===" % blocks)
        print("<<< ours")
        print("\n".join(ours))
        print("--- theirs")
        print("\n".join(theirs))
        print(">>>")
        if any("draft_has_own_head" in l for l in theirs):
            out.extend(GET if l == OLD else l for l in theirs)
        else:
            out.extend(ours)
        mode = None
        continue
    (ours if mode == "ours" else theirs if mode == "theirs" else out).append(line)
assert mode is None and blocks >= 1, "expected conflict blocks, got %d" % blocks
s = "\n".join(out)
assert s.count(GET) == 1, "getattr line count %d" % s.count(GET)
assert "and not draft_has_own_head" in s, "own-head addition missing"
assert OLD not in s, "old load_format form still present"
open(p, "w").write(s)
print("resolved", blocks, "block(s) -> getattr + own-head addition")
