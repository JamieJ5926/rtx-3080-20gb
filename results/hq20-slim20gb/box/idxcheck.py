#!/usr/bin/env python3
import json, os, sys, tempfile
import vllm.model_executor.model_loader.default_loader as dl
from vllm.model_executor.model_loader.default_loader import DefaultModelLoader

real = "/home/jamie/models/q38-lemin"
names = [f for f in os.listdir(real) if f.endswith("index.json")]
assert names, "no index file found in the model dir"
index_name = names[0]
tmp = tempfile.mkdtemp(prefix="/home/jamie/hq20/idxcheck.")
with open(os.path.join(tmp, index_name), "w") as f:
    json.dump({"weight_map": {"model.layers.0.q_proj.weight": "a.safetensors"}}, f)
print("fixture dir:", tmp, "index file name derived from real dir:", index_name)


class Src:
    model_or_path = tmp
    prefix = ""


loader = DefaultModelLoader.__new__(DefaultModelLoader)
try:
    list(loader._get_mtp_weights(Src))
    print("INDEX_CHECK FAIL: no error raised")
    sys.exit(1)
except ValueError as e:
    msg = str(e)
    ok = "mtp.fc." in msg and "mtp.layers." in msg and "missing" in msg.lower()
    print("INDEX_CHECK", "PASS" if ok else "FAIL", "raised ValueError:", msg)
    sys.exit(0 if ok else 1)
except Exception as e:
    print("INDEX_CHECK FAIL wrong exception:", repr(e))
    sys.exit(1)
