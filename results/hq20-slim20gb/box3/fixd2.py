#!/usr/bin/env python3
p = "/home/jamie/vllm-slim-src/vllm/v1/spec_decode/llm_base_proposer.py"
s = open(p).read()
anchor = "        from vllm.compilation.backends import set_model_tag\n"
norm = anchor + "        from vllm.config.load import LoadConfig\n" + "        draft_load_config = self.speculative_config.draft_load_config or LoadConfig()\n"
assert s.count(anchor) == 1, "anchor count %d" % s.count(anchor)
s = s.replace(anchor, norm)
old1 = "                        self.speculative_config.draft_load_config\n"
assert s.count(old1) == 1, "site1 count %d" % s.count(old1)
s = s.replace(old1, "                        draft_load_config\n")
old2 = "                    load_config=self.speculative_config.draft_load_config,\n"
assert s.count(old2) == 1, "site2 count %d" % s.count(old2)
s = s.replace(old2, "                    load_config=draft_load_config,\n")
assert s.count("self.speculative_config.draft_load_config") == 2, "residual raw derefs %d (expect 2: the normalize line and the guarded getattr)" % s.count("self.speculative_config.draft_load_config")
open(p, "w").write(s)
print("class fix applied to _get_model")
