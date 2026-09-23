#!/usr/bin/env python3
p = "/home/jamie/hq20/measure.py"
s = open(p).read()
old = '''            delta = d["choices"][0].get("delta", {}) if d.get("choices") else {}
            piece = delta.get("content") or delta.get("reasoning_content") or ""
            if piece:
                if ttft is None:
                    ttft = time.time()
                text.append(piece)'''
new = '''            delta = d["choices"][0].get("delta", {}) if d.get("choices") else {}
            piece = ""
            for _k, _v in delta.items():
                if _k in ("role", "tool_calls") or not isinstance(_v, str) or not _v:
                    continue
                piece = _v
                break
            if piece:
                if ttft is None:
                    ttft = time.time()
                    raw_first.append(d)
                text.append(piece)'''
assert s.count(old) == 1, "delta block count %d" % s.count(old)
s = s.replace(old, new)
oinit = "    t0 = time.time()\n    ttft = None\n"
ninit = "    t0 = time.time()\n    ttft = None\n    raw_first = []\n"
assert s.count(oinit) == 1
s = s.replace(oinit, ninit)
oret = '    return {\n        "ttft": (ttft - t0) if ttft else None,'
nret = '    return {\n        "raw_first_chunks": raw_first[:3],\n        "ttft": (ttft - t0) if ttft else None,'
assert s.count(oret) == 1
s = s.replace(oret, nret)
open(p, "w").write(s)
print("measure.py stream detector widened (any delta string counts, first chunks captured)")
