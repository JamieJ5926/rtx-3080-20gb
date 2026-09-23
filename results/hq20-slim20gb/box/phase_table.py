#!/usr/bin/env python3
import json, sys


def gib(n):
    try:
        return round(int(n) / 2 ** 30, 3)
    except Exception:
        return n


def main():
    path = sys.argv[1]
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    print("phase\tpid\talloc_GiB\treserved_GiB\tmax_alloc_GiB\tfree_dev_GiB\trss_GiB\tresident_GiB\tdetail")
    for r in rows:
        free, total = r.get("mem_get_info", ["-", "-"])
        detail = {k: v for k, v in r.items() if k not in (
            "phase", "ts", "pid", "mem_allocated", "mem_reserved", "mem_max_allocated",
            "mem_get_info", "rss_bytes", "resident_bytes", "model_path", "revision",
            "config", "dtype_enum", "dtype_name", "alloc_conf", "device")}
        print("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
            r.get("phase"), r.get("pid"), gib(r.get("mem_allocated")), gib(r.get("mem_reserved")),
            gib(r.get("mem_max_allocated")), gib(free), gib(r.get("rss_bytes")),
            gib(r.get("resident_bytes")), json.dumps(detail, sort_keys=True, default=str)))
    packs = [r for r in rows if r.get("phase") == "p4_after_marlin_repack"]
    print("\np4_marlin_repack_count=%d" % len(packs))
    for r in packs[:60]:
        print("  repack module=%s param=%s kernel=%s dtypes=%s" % (
            r.get("module"), r.get("param"), r.get("kernel"), json.dumps(r.get("dtypes", {}), sort_keys=True)))
    p5 = [r for r in rows if str(r.get("phase", "")).startswith("p5_")]
    for r in p5:
        print("p5_identity:", json.dumps({k: v for k, v in r.items() if "identity" in k or k in ("shared_modules", "draft_only")}, sort_keys=True))
    p6a = [r for r in rows if r.get("phase") == "p6a_after_int4_scratch_alloc"]
    for r in p6a:
        print("p6a_scratch:", json.dumps(r.get("plan", {}), sort_keys=True), "buffers:", json.dumps(r.get("buffers", {}), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
