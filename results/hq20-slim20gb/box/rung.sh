#!/bin/bash
# One fit rung: $1 = tag, $2 = MAX_LEN, $3 = fp8|int4 (default fp8)
set -u
TAG="${1:?usage: rung.sh TAG MAX_LEN fp8|int4}"
MAX_LEN="${2:?usage: rung.sh TAG MAX_LEN fp8|int4}"
MODE="${3:-fp8}"
GPU_UTIL="${GPU_UTIL:-0.95}"
if [ "$MODE" = "int4" ]; then
  EXTRA_ARGS="--kv-cache-dtype int4_per_token_head --attention-backend TRITON_ATTN"
else
  EXTRA_ARGS=""
fi
LOG=/home/jamie/hq20/ladder-$TAG.log
echo "=== RUNG $TAG MAX_LEN=$MAX_LEN MODE=$MODE GPU_UTIL=$GPU_UTIL ==="
echo "=== residency before ==="
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
HQT=1 HQTRACE=/home/jamie/hq20/ladder-$TAG-trace.jsonl HQMODEL=/home/jamie/models/q38-lemin PYTHONPATH=/home/jamie/hq20 CUDA_HOME=/opt/cuda PATH=/opt/cuda/bin:$PATH MODEL=/home/jamie/models/q38-lemin SPEC=mtp CTX=long MAX_LEN=$MAX_LEN GPU_UTIL=$GPU_UTIL PORT=18020 EXTRA_ARGS="$EXTRA_ARGS" nohup /home/jamie/qwen-arm20/single-user/start_qwen.sh > "$LOG" 2>&1 &
echo "arm launched pid=$!"
HEALTH=0
for i in $(seq 1 40); do
  sleep 15
  if curl -sf http://127.0.0.1:18020/health > /dev/null 2>&1; then
    echo "HEALTH_OK after $((i*15))s"
    HEALTH=1
    break
  fi
  if ! pgrep -f "vllm serve" > /dev/null; then
    echo "ARM_DIED"
    break
  fi
done
if [ "$HEALTH" = 1 ]; then
  echo "=== smoke ==="
  /home/jamie/venv-slim20/bin/python /home/jamie/hq20/measure.py --fill 0 --n 1 --max-tokens 600 --label "$TAG" --out /home/jamie/hq20/smoke-$TAG.txt
fi
echo "=== residency after ==="
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
echo "=== kv pool ==="
grep -oE "GPU KV cache size: [0-9,]+ tokens" "$LOG" | tail -1
grep -oE "Maximum concurrency for [0-9,]+ tokens per request: [0-9.]+x" "$LOG" | tail -1
echo "=== checkpoint reads ==="
grep -c "Checkpoint size" "$LOG"
echo "=== log tail ==="
tail -6 "$LOG"
echo "=== stop arm ==="
pkill -f "vllm serve" || true
sleep 5
nvidia-smi --query-gpu=memory.used --format=csv,noheader
echo "=== RUNG $TAG done ==="
