#!/usr/bin/env bash
# Long-context agent climb on IQ3_S. Runs on the Mac. For each arm: write its config on the PC, restart the server
# with it, run agentic_bench.py, and log one JSON line with the PC load before and after.
# Usage: bash climb_queue.sh [arm ...]   (default: every arm in ARMS order)
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/climb.jsonl
CORPUS=/Users/jamie/Projects/active/mixed-cluster-wt/strata-upstream/src
BASE_CFG=${BASE_CFG:-runs/serve/r30-131k.json}
MODEL=${MODEL:-qwen3.8-flash-next-iq3_s}
PC() { ssh -n -o BatchMode=yes -o ConnectTimeout=15 -o ControlMaster=no -o ControlPath=none home-pc-1 "$@"; }

# arm name | args to set (flag=value, comma separated) | env (K=V, comma separated)
ARMS=(
  "base-r30|--resident-budget-gib=30|"
  "vram832|--resident-budget-gib=30,--vram-reserve-mib=832|"
  "chunk16k|--resident-budget-gib=30,--prefill=auto:16384|"
  "kvq4|--resident-budget-gib=30,--kv=q4_0|"
  "overlap|--resident-budget-gib=30|STRATA_ADAPT_OVERLAP_RESIDENT=1"
  "kvprefetch|--resident-budget-gib=30|STRATA_KV_PREFETCH=1"
  "convcache|--resident-budget-gib=30,--conversation-cache-mib=2048,--prompt-cache=12|"
  "nomtp|--resident-budget-gib=30,--spec=0|"
  "nomtp|--resident-budget-gib=30,--spec=0|"
  "base-46g|--resident-budget-gib=30|"
  "combo-46g|--resident-budget-gib=30,--prefill=auto:16384,--kv=q4_0|STRATA_KV_PREFETCH=1"
  "b52-base|--resident-budget-gib=30|"
  "b52-chunk16k|--resident-budget-gib=30,--prefill=auto:16384|"
  "b52-r32|--resident-budget-gib=32|"
  "b52-r34|--resident-budget-gib=34|"
  "b52-kvq4|--resident-budget-gib=30,--kv=q4_0|"
  "b52-kvprefetch|--resident-budget-gib=30|STRATA_KV_PREFETCH=1"
  "b52-promptcache|--resident-budget-gib=30,--prompt-cache=12,--prompt-cache-every=4096|"
  "b52-spec5|--resident-budget-gib=30,--spec=5|"
  "f256-r34-q4|--resident-budget-gib=34,--kv=q4_0,--max-context=262144|"
  "f256-r34-q4-b|--resident-budget-gib=34,--kv=q4_0,--max-context=262144|"
  "f256-r34-int8|--resident-budget-gib=34,--kv=int8,--max-context=262144|"
  "f256-r34-int8-c16|--resident-budget-gib=34,--kv=int8,--max-context=262144,--prefill=auto:16384|"
  "f256-r34-int8-spec2|--resident-budget-gib=34,--kv=int8,--max-context=262144,--spec=2|"
  "f256-r34-int8-spec3|--resident-budget-gib=34,--kv=int8,--max-context=262144,--spec=3|"
  "f256-r34-int8-spec6|--resident-budget-gib=34,--kv=int8,--max-context=262144,--spec=6|"
  "f256-r36-int8|--resident-budget-gib=36,--kv=int8,--max-context=262144|"
  "f256-r32-int8|--resident-budget-gib=32,--kv=int8,--max-context=262144|"
  "f256-r34-k8v4|--resident-budget-gib=34,--kv=k8v4,--max-context=262144|"
  "f256-r34-int8-p32|--resident-budget-gib=34,--kv=int8,--max-context=262144,--prefill=auto:32768|"
  "f256-r34-int8-minp7|--resident-budget-gib=34,--kv=int8,--max-context=262144,--spec-min-p=0.7|"
  "f256-r34-int8-swaps|--resident-budget-gib=34,--kv=int8,--max-context=262144,--adapt-swaps=24|"
  "orca-r34|--resident-budget-gib=34|"
  "orca-r34-b|--resident-budget-gib=34|"
  "orca-r36|--resident-budget-gib=36|"
  "orca-r36-q4|--resident-budget-gib=36,--kv=q4_0|"
  "orca-r37-q4|--resident-budget-gib=37,--kv=q4_0|"
  "orca-r32|--resident-budget-gib=32|"
)

want=("$@")
for row in "${ARMS[@]}"; do
  IFS='|' read -r arm sets envs <<<"$row"
  if [ ${#want[@]} -gt 0 ] && [[ ! " ${want[*]} " =~ " $arm " ]]; then continue; fi
  cfg=/home/jamie/mixed-cluster/runs/serve/climb-$arm.json
  PC "cd /home/jamie/mixed-cluster && python3 - '$cfg' '$sets' '$envs' '$BASE_CFG' <<'EOF'
import json, sys
cfg, sets, envs, base = sys.argv[1:5]
c = json.load(open(base))
a = c['args']
for s in filter(None, sets.split(',')):
    k, v = s.split('=', 1)
    if k == '--spec' and v == '0':
        for f in ('--spec', '--spec-min-p', '--mtp'):
            if f in a:
                i = a.index(f); del a[i:i + 2]
        continue
    if k in a: a[a.index(k) + 1] = v
    else: a += [k, v]
env = dict(c.get('env') or {})
for e in filter(None, envs.split(',')):
    k, v = e.split('=', 1); env[k] = v
if env: c['env'] = env
c['log'] = '/home/jamie/mixed-cluster/runs/serve/engine-climb-' + cfg.split('climb-')[1].replace('.json', '.log')
json.dump(c, open(cfg, 'w'), indent=1)
EOF" || { echo "{\"arm\":\"$arm\",\"error\":\"config\"}" >>"$OUT"; continue; }
  if ! PC "timeout 420 bash /home/jamie/mixed-cluster/runs/serve/serve-swap.sh $cfg"; then
    echo "{\"arm\":\"$arm\",\"error\":\"server did not start\"}" | tee -a "$OUT"; continue
  fi
  load0=$(PC "cut -d' ' -f1 /proc/loadavg")
  line=$(CORPUS_DIR=$CORPUS python3 "$HERE/agentic_bench.py" http://127.0.0.1:18080/v1 "$MODEL" "$arm" 2>&1 | tail -1)
  load1=$(PC "cut -d' ' -f1 /proc/loadavg; grep -E '^high ' /sys/fs/cgroup/user.slice/user-\$(id -u).slice/user@\$(id -u).service/cluster.slice/memory.events | cut -d' ' -f2; grep MemAvailable /proc/meminfo | tr -s ' ' | cut -d' ' -f2" | tr '\n' ' ')
  python3 - "$arm" "$load0" "$load1" "$line" >>"$OUT" <<'EOF'
import json, sys
arm, l0, l1, line = sys.argv[1:5]
try:
    d = json.loads(line)
except ValueError:
    d = {"error": line[-300:]}
p = l1.split()
d.update(arm=arm, load_before=float(l0 or 0), load_after=float(p[0]) if p else None,
         memhigh_events=int(p[1]) if len(p) > 1 else None, memavail_kb=int(p[2]) if len(p) > 2 else None)
print(json.dumps(d))
EOF
  echo "logged $arm"
done
