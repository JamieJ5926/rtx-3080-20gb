#!/bin/bash
# h61 arm runner template. Runs ON THE BOX. One variable per arm.
# Decode is the metric. Prefill is guard rail only.
# Usage. Copy this file to /tmp/h61-arm.sh on the box, set FLAGS and TAG, then run.
# Do not run while SwaHybridRung holds the GPU. Wait for its release first.
set -u
TAG="${TAG:-h61-baseline}"
FLAGS="${FLAGS:-}"
LAUNCHER=/home/jamie/llama/llama-serve.sh
RUN_DIR=/home/jamie/Projects/active/rtx-3080-20gb-omarchy/results/h61-overnight-ladder
mkdir -p "$RUN_DIR"
echo "=== $TAG ==="
echo "flags: $FLAGS"
kill -STOP 34846
systemctl --user stop llama-watchdog.service
pkill -f llama-server || true
sleep 3
cp "$LAUNCHER" "$RUN_DIR/launcher.before-$TAG"
printf '%s\n' '#!/bin/bash' "exec /usr/bin/llama-server $FLAGS --jinja --port 8083 --host 0.0.0.0" > "$LAUNCHER"
chmod +x "$LAUNCHER"
cat "$LAUNCHER"
systemctl --user start llama-watchdog.service
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8083/health > /dev/null 2>&1; then break; fi
  sleep 5
done
curl -sf http://127.0.0.1:8083/health || { echo "REJECT $TAG health failed"; kill -CONT 34846; exit 1; }
ps aux | grep '[l]lama-server' | head -n 5
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
python3 "$RUN_DIR/measure-h61.py" --fill 0 --n 5 --out "$RUN_DIR/$TAG-fresh.txt"
python3 "$RUN_DIR/measure-h61.py" --fill 33355 --n 5 --out "$RUN_DIR/$TAG-33k.txt"
python3 "$RUN_DIR/measure-h61.py" --fill 91655 --n 5 --out "$RUN_DIR/$TAG-91k.txt"
python3 "$RUN_DIR/quality-probe.py" --out "$RUN_DIR/$TAG-quality.txt" || { echo "REJECT $TAG quality failed"; kill -CONT 34846; exit 1; }
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
kill -CONT 34846
echo "done $TAG"
