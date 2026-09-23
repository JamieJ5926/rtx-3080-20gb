#!/usr/bin/env python3
p = "/home/jamie/hq20/measure.py"
s = open(p).read()
old = '''            if d.get("choices") and d["choices"][0].get("delta", {}).get("content"):
                if ttft is None:
                    ttft = time.time()
                text.append(d["choices"][0]["delta"]["content"])'''
new = '''            delta = d["choices"][0].get("delta", {}) if d.get("choices") else {}
            piece = delta.get("content") or delta.get("reasoning_content") or ""
            if piece:
                if ttft is None:
                    ttft = time.time()
                text.append(piece)'''
assert s.count(old) == 1, "delta block count %d" % s.count(old)
s = s.replace(old, new)
o1 = '    med_dec = statistics.median(r["decode_tok_s"] for r in rows)'
n1 = '    med_dec = statistics.median([r["decode_tok_s"] for r in rows] or [0])'
o2 = '    med_e2e = statistics.median(r["e2e_tok_s"] for r in rows)'
n2 = '    med_e2e = statistics.median([r["e2e_tok_s"] for r in rows] or [0])'
o3 = '    med_ttft = statistics.median(r["ttft"] for r in rows if r["ttft"])'
n3 = '    med_ttft = statistics.median([r["ttft"] for r in rows if r["ttft"]] or [0])'
o4 = '    med_pre = statistics.median(r["prefill_derived_tok_s"] for r in rows)'
n4 = '    med_pre = statistics.median([r["prefill_derived_tok_s"] for r in rows] or [0])'
for o, n in ((o1, n1), (o2, n2), (o3, n3), (o4, n4)):
    if s.count(o) == 1:
        s = s.replace(o, n)
open(p, "w").write(s)
print("measure.py hardened (reasoning_content counted, empty medians guarded)")
