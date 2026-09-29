#!/bin/bash
# arm-run.sh <env-file> — one GPU arm cycle: suppressor on, production down, target
# server up, battery, production restored and health-verified. Idempotent end state.
set -u
ENVF="${1:?usage: arm-run.sh <env-file>}"
. "$ENVF"
: "${RUN_ID:?set RUN_ID}"
: "${MODEL:?set MODEL}"
R=/home/jamie/hq20/hillclimb
LOCKDIR=/tmp/hillclimb-arm.lock
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  LP=$(cat "$LOCKDIR/pid" 2>/dev/null || true)
  if [ -n "$LP" ] && kill -0 "$LP" 2>/dev/null; then
    echo "arm already running pid=$LP; refusing" >> /home/jamie/hq20/hillclimb/arm-lock-refused.log
    exit 1
  fi
  rm -rf "$LOCKDIR"; mkdir "$LOCKDIR"
fi
echo $$ > "$LOCKDIR/pid"
trap "rm -rf $LOCKDIR" EXIT
D=$R/runs/$RUN_ID
mkdir -p "$D"
rm -f "$D/DONE"
CTX="${CTX:-196608}"
KV_ARGS="${KV_ARGS:--ctk q4_0 -ctv q4_0}"
EXTRA_ARGS="${EXTRA_ARGS:-}"
UB="${UB:-256}"
SPEC_ARGS="${SPEC_ARGS:---spec-type draft-mtp}"
SWA_ARGS="${SWA_ARGS:---override-kv qwen35.attention.sliding_window=int:4096 --override-kv qwen35.attention.swa_global_layers=int:8}"
FILLS="${FILLS:-0 33355 60000}"
AGENT_BENCH="${AGENT_BENCH:-no}"
RECALL_SEED="${RECALL_SEED:-2026092330}"
L=/home/jamie/llama.cpp-turboq-mtp/build/bin/llama-server
export HILLCLIMB_BASE=http://127.0.0.1:8083
export HILLCLIMB_PORT=8083
log() { echo "$(date -u +%H:%M:%S) $*" >> "$D/arm.log"; }

suppress_watchdog() {
  systemctl --user stop llama-watchdog.service 2>/dev/null
  while [ -f "$D/SUPPRESS" ]; do
    P=$(ps -eo pid,args | awk '/llama-watchdog\.sh/ && !/awk/ {print $1}')
    [ -n "$P" ] && kill $P 2>/dev/null
    sleep 5
  done
} 
stop_suppressor() { rm -f "$D/SUPPRESS"; }

restore() {
  stop_suppressor
  sleep 6
  pkill -x llama-server 2>/dev/null
  sleep 4
  cp /home/jamie/llama/llama-serve.sh.h76-savepoint-h77 /home/jamie/llama/llama-serve.sh
  chmod +x /home/jamie/llama/llama-serve.sh
  systemctl --user start llama-watchdog.service 2>/dev/null
  for i in $(seq 1 24); do
    sleep 5
    curl -sf -m 5 http://127.0.0.1:8083/health >/dev/null 2>&1 && { log RESTORE_OK; break; }
  done
  curl -sf -m 5 http://127.0.0.1:8083/health >/dev/null 2>&1 || log RESTORE_FAIL
  date -u +%Y-%m-%dT%H:%M:%SZ > "$D/DONE"
  exit 0
}
trap restore EXIT INT TERM

log "ARM $RUN_ID model=$(basename "$MODEL") ctx=$CTX ub=$UB"
touch "$D/SUPPRESS"
( suppress_watchdog ) &
sleep 2
pkill -x llama-server 2>/dev/null
for i in $(seq 1 20); do pgrep -x llama-server >/dev/null || break; sleep 2; done
FREE=0
for i in $(seq 1 60); do
  FREE=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
  [ "$FREE" -ge 19047 ] 2>/dev/null && break
  pgrep -x llama-server >/dev/null 2>&1 && pkill -x llama-server 2>/dev/null
  sleep 2
done
log "prearm free=${FREE}MiB"
[ "$FREE" -ge 19047 ] 2>/dev/null || { log PREARM_FAIL; exit 1; }

LD_LIBRARY_PATH=/home/jamie/llama.cpp-turboq-mtp/build/bin \
  setsid nohup $L -m "$MODEL" -ngl 99 -c "$CTX" --parallel 1 $KV_ARGS -fa on -ub "$UB" \
  $SPEC_ARGS $SWA_ARGS --jinja --port 8083 --host 0.0.0.0 $EXTRA_ARGS \
  > "$D/serve.log" 2>&1 &
OK=0
for i in $(seq 1 30); do
  sleep 10
  curl -sf -m 5 http://127.0.0.1:8083/health >/dev/null 2>&1 && { OK=1; log "HEALTH_OK $((i*10))s"; break; }
done
[ "$OK" = 1 ] || { log BOOT_FAIL; tail -5 "$D/serve.log" >> "$D/arm.log"; exit 1; }

for F in $FILLS; do
  python3 /home/jamie/hq20/measure.py --fill "$F" --n 5 --max-tokens 600 \
    --label "$RUN_ID" --out "$D/fill$F.txt" >> "$D/arm.log" 2>&1 || log "MEASURE_FAIL $F"
done
if [ "${CACHE_PROBE:-no}" = yes ]; then
  timeout 600 python3 /home/jamie/hq20/hillclimb/cache-probe.py 8083 8000 >> "$D/arm.log" 2>&1 || log CACHE_PROBE_FAIL
fi
if [ "$AGENT_BENCH" = yes ]; then
  python3 /home/jamie/hq20/hillclimb/tempest-bench.py --port 8083 --out "$D/agent" \
    --depth 8192 20480 --burst 2 >> "$D/arm.log" 2>&1 || log AGENT_BENCH_FAIL
fi
python3 /home/jamie/hq20/recall.py --fill 60000 --seed "$RECALL_SEED" \
  --out "$D/recall60000.txt" >> "$D/arm.log" 2>&1 || log RECALL_FAIL
python3 /home/jamie/hq20/qualityfixed.py --out "$D/quality.txt" >> "$D/arm.log" 2>&1 || log QUALITY_FAIL
log ARM_COMPLETE
restore
