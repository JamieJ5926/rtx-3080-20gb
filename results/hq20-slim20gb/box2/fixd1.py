#!/usr/bin/env python3
p = "/home/jamie/vllm-slim-src/vllm/v1/spec_decode/llm_base_proposer.py"
s = open(p).read()
old = '            and self.speculative_config.draft_load_config.load_format in ("auto", "hf", "safetensors")\n'
new = '            and getattr(self.speculative_config.draft_load_config, "load_format", "auto") in ("auto", "hf", "safetensors")\n'
assert s.count(old) == 1, "expected exactly one can_share load_format line, found %d" % s.count(old)
open(p, "w").write(s.replace(old, new))
print("patched", p)
