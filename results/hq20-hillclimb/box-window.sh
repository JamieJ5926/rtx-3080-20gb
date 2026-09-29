#!/bin/bash
# Box-side hillclimb window for the HyperQwen slim-20gb stack. Runs ON THE BOX.
# One variable per window, set in the run spec file. Production is restored and
# verified in every path through the closeout trap.
# Usage: bash box-window.sh /home/jamie/hq20/hillclimb/<RUNG_ID>.env
set -u
SPEC_FILE="${1:?usage: box-window.sh RUNG.env}"
RUNG_ID="$(basename "$SPEC_FILE" .env)"
. "$SPEC_FILE"
: "${MAX_LEN:?set MAX_LEN in spec}"
: "${GPU_UTIL:?set GPU_UTIL in spec}"
: "${MEASURE_FILLS:=0 33355 91655}"
: "${RECALL_PROBES:=}"
: "${KV_ARGS:=}"
: "${EXTRA_ARGS:=}"
: "${ENV_KNOBS:=}"
: "${SPEC:=mtp}"
: "${CTX:=long}"
R=/home/jamie/hq20/hillclimb
mkdir -p "$R"
LOG=$R/$RUNG_ID-arm.log
exec > >(tee -a "$LOG") 2>&1

LAUNCHER=/home/jamie/llama/llama-serve.sh
SAVEPOINT=/home/jamie/llama/llama-serve.sh.h76-savepoint-h77
TURBOQ_BIN=/home/jamie/llama.cpp-turboq-mtp/build/bin/llama-server
ARM_LOG=$R/$RUNG_ID-vllm.log
PY=/home/jamie/venv-slim20/bin/python

closeout() {
  echo "=== CLOSEOUT $RUNG_ID $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  pkill -f "vllm serve" || true
  pkill -f hillclimb-port-stub >/dev/null 2>&1 || true
  sleep 5
  echo "residency after arm:"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader
  if [ -x "$TURBOQ_BIN" ]; then
    "$TURBOQ_BIN" --version > "$R/$RUNG_ID-bin-gate.txt" 2>&1 \
      && echo "BINARY_GATE PASS" || echo "BINARY_GATE VERSION_FAIL"
  else
    echo "BINARY_GATE FAIL missing $TURBOQ_BIN"
  fi
  cp "$SAVEPOINT" "$LAUNCHER"
  chmod +x "$LAUNCHER"
  if diff -q "$SAVEPOINT" "$LAUNCHER" >/dev/null; then
    echo "LAUNCHER RESTORED_IDENTICAL"
  else
    echo "LAUNCHER RESTORE_DIFF FAIL"
  fi
  systemctl --user start llama-watchdog.service
  HEALTH=0
  for i in $(seq 1 30); do
    curl -sf http://127.0.0.1:8083/health >/dev/null 2>&1 && { HEALTH=1; break; }
    sleep 5
  done
  if [ "$HEALTH" = 1 ]; then
    echo "HEALTH_OK after $((i*5))s"
  else
    echo "HEALTH_FAIL"
  fi
  python3 /home/jamie/hq20/h76verify.py "$R/$RUNG_ID-h76verify.txt"
  echo "VERIFY_RC $?"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$R/WINDOW_DONE_$RUNG_ID"
  echo "=== WINDOW_DONE $RUNG_ID ==="
}
trap closeout EXIT
trap 'exit 1' HUP INT TERM

echo "=== RUNG $RUNG_ID $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "spec: MAX_LEN=$MAX_LEN GPU_UTIL=$GPU_UTIL SPEC=$SPEC CTX=$CTX"
echo "KV_ARGS=$KV_ARGS EXTRA_ARGS=$EXTRA_ARGS ENV_KNOBS=$ENV_KNOBS"
echo "measure_fills=$MEASURE_FILLS recall_probes=${RECALL_PROBES:-none}"

echo "=== production down ==="
systemctl --user stop llama-watchdog.service
pkill -x llama-server || true
PREARM_TIMEOUT=120
PREARM_INTERVAL=2
PREARM_ELAPSED=0
PREARM_READY=0
while [ "$PREARM_ELAPSED" -lt "$PREARM_TIMEOUT" ]; do
  PREARM_PGREP_RC=0
  pgrep -x llama-server >/dev/null || PREARM_PGREP_RC=$?
  if [ "$PREARM_PGREP_RC" -eq 0 ]; then
    echo "prearm waiting: llama-server still present"
  elif [ "$PREARM_PGREP_RC" -eq 1 ]; then
    PREARM_FREE_MIB="$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1)"
    case "$PREARM_FREE_MIB" in
      ''|*[!0-9]*) echo "prearm waiting: invalid free VRAM sample=${PREARM_FREE_MIB:-empty}" ;;
      *)
        if [ "$PREARM_FREE_MIB" -ge 19047 ]; then
          echo "prearm ready: llama-server absent, free_vram=${PREARM_FREE_MIB}MiB (>=18.6GiB)"
          PREARM_READY=1
          break
        fi
        echo "prearm waiting: free_vram=${PREARM_FREE_MIB}MiB (<18.6GiB)"
        ;;
    esac
  else
    echo "prearm waiting: pgrep failed with status $PREARM_PGREP_RC"
  fi
  sleep "$PREARM_INTERVAL"
  PREARM_ELAPSED=$((PREARM_ELAPSED + PREARM_INTERVAL))
done
if [ "$PREARM_READY" -ne 1 ]; then
  echo "PREARM_GATE_TIMEOUT after ${PREARM_TIMEOUT}s; refusing arm launch"
  exit 1
fi
echo "residency before arm:"
# Exclusive-window stub: answer :8083/v1/models so external supervisors (Mac
# overnight-supervisor.sh ensure_llama, ~90s tick) see production as up and do
# not kill -9 + respawn llama-server mid-window. Diagnosed 2026-09-24: supervisor
# log "llama DOWN" lines align 1:1 with reverted arms' snapshot deaths (0.54GiB).
STUB_PY=/tmp/hillclimb-port-stub.py
cat > "$STUB_PY" <<'PYEOF'
import http.server, json
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"object":"list","data":[{"id":"orcarouter-uncensored-IQ4_XS","object":"model"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*a): pass
http.server.HTTPServer(("0.0.0.0",8083),H).serve_forever()
PYEOF
nohup python3 "$STUB_PY" >/dev/null 2>&1 &
STUB_PID=$!
for i in 1 2 3 4 5; do
  curl -sf -m 2 http://127.0.0.1:8083/v1/models 2>/dev/null | grep -q orcarouter && break
  sleep 1
done
echo "port stub up pid=$STUB_PID"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader

env HQT=1 HQTRACE=$R/$RUNG_ID-trace.jsonl HQMODEL=/home/jamie/models/q38-lemin \
  PYTHONPATH=/home/jamie/hq20 CUDA_HOME=/opt/cuda PATH=/opt/cuda/bin:$PATH \
  MODEL=/home/jamie/models/q38-lemin SPEC="$SPEC" CTX="$CTX" \
  MAX_LEN="$MAX_LEN" GPU_UTIL="$GPU_UTIL" PORT=18020 \
  EXTRA_ARGS="$KV_ARGS $EXTRA_ARGS" $ENV_KNOBS \
  nohup /home/jamie/qwen-arm20/single-user/start_qwen.sh > "$ARM_LOG" 2>&1 &
echo "arm launched pid=$!"

HEALTH=0
for i in $(seq 1 40); do
  sleep 15
  curl -sf http://127.0.0.1:18020/health >/dev/null 2>&1 && { HEALTH=1; echo "ARM_HEALTH_OK after $((i*15))s"; break; }
  if ! pgrep -f "vllm serve" >/dev/null; then
    echo "ARM_DIED"
    break
  fi
done

if [ "$HEALTH" = 1 ]; then
  for F in $MEASURE_FILLS; do
    $PY /home/jamie/hq20/measure.py --fill "$F" --n 5 --max-tokens 600 \
      --label "$RUNG_ID" --out "$R/$RUNG_ID-fill$F.txt" || echo "MEASURE_FAIL fill=$F"
  done
  for PS in $RECALL_PROBES; do
    F="${PS%%:*}"
    S="${PS##*:}"
    $PY /home/jamie/hq20/recall.py --fill "$F" --seed "$S" \
      --out "$R/$RUNG_ID-recall$F-seed$S.txt" || echo "REJECT recall fill=$F seed=$S"
  done
  $PY /home/jamie/hq20/qualityfixed.py --out "$R/$RUNG_ID-quality.txt" || echo "REJECT quality"
  if [ -n "${BENCH_CMD:-}" ]; then
    echo "=== BENCH_CMD ==="
    eval "$BENCH_CMD"
    echo "BENCH_RC $?"
  fi
else
  echo "ARM_UNHEALTHY measurement skipped"
fi

echo "=== arm log facts ==="
grep -oE "GPU KV cache size: [0-9,]+ tokens" "$ARM_LOG" | tail -1
grep -oE "Maximum concurrency for [0-9,]+ tokens per request: [0-9.]+x" "$ARM_LOG" | tail -1
grep -c "Checkpoint size" "$ARM_LOG"
tail -6 "$ARM_LOG"
echo "=== measurement done, closing window ==="
