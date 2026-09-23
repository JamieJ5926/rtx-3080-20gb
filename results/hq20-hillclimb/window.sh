#!/bin/bash
# Mac-side window owner for the HyperQwen slim-20gb hillclimb. Runs ON THE MAC.
# Announces, freezes the overnight supervisor, gates idle traffic, dispatches the
# box window, polls to completion, pulls receipts, resumes the supervisor.
# Usage: window.sh RUNG_ID /path/to/RUNG_ID.env
set -u
RUNG_ID="${1:?usage: window.sh RUNG_ID RUNG.env}"
SPEC_SRC="${2:?usage: window.sh RUNG_ID RUNG.env}"
BOX=jamie@100.112.17.108
R="$(cd "$(dirname "$0")" && pwd)"
RECEIPTS="$R/receipts"
mkdir -p "$RECEIPTS"
BOX_R=/home/jamie/hq20/hillclimb
SSH="ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=20 $BOX"

resume_supervisor() {
  kill -CONT 34846 2>/dev/null && echo "SUPERVISOR resumed $(date -u +%H:%M:%SZ)"
}
trap resume_supervisor EXIT

echo "=== ANNOUNCE window $RUNG_ID $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "variable under test and delta:"
sed 's/^/  /' "$SPEC_SRC"
echo "=== ANNOUNCE window $RUNG_ID $(date -u +%Y-%m-%dT%H:%M:%SZ) spec=$(basename "$SPEC_SRC") ===" >> "$RECEIPTS/ANNOUNCE.log"

if kill -STOP 34846 2>/dev/null; then
  echo "SUPERVISOR frozen $(date -u +%H:%M:%SZ)"
else
  echo "SUPERVISOR_FREEZE_FAIL pid 34846 not found"
fi

echo "=== idle gate against live traffic ==="
REQLOG=/home/jamie/llama/llama-server.log
IDLE=0
PREV=unset
for i in $(seq 1 20); do
  CUR=$($SSH "stat -c %s $REQLOG 2>/dev/null || echo 0")
  echo "request_log_bytes=$CUR poll=$i"
  if [ "$PREV" != "unset" ] && [ "$CUR" = "$PREV" ] && [ "$CUR" != "0" ]; then IDLE=1; break; fi
  PREV=$CUR
  sleep 30
done
if [ "$IDLE" != 1 ]; then
  echo "IDLE_GATE_FAIL log_bytes=$CUR, window aborted, production left up"
  echo "ABORTED_IDLE_GATE $RUNG_ID log_bytes=$CUR $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$RECEIPTS/ANNOUNCE.log"
  exit 1
fi

$SSH "mkdir -p $BOX_R"
scp -q "$SPEC_SRC" "$BOX:$BOX_R/$RUNG_ID.env"
scp -q "$R/box-window.sh" "$BOX:$BOX_R/box-window.sh"

echo "=== box window start $(date -u +%H:%M:%SZ) ==="
$SSH "rm -f $BOX_R/WINDOW_DONE_$RUNG_ID; nohup /bin/bash $BOX_R/box-window.sh $BOX_R/$RUNG_ID.env > $BOX_R/$RUNG_ID-ssh.log 2>&1 < /dev/null & echo BOX_PID=\$!"

DONE=0
for i in $(seq 1 180); do
  sleep 60
  if $SSH "test -f $BOX_R/WINDOW_DONE_$RUNG_ID" 2>/dev/null; then
    DONE=1
    echo "window complete after ${i}m"
    break
  fi
  $SSH "tail -1 $BOX_R/$RUNG_ID-arm.log 2>/dev/null" | sed "s/^/[${i}m] /"
done
if [ "$DONE" != 1 ]; then
  echo "WINDOW_POLL_TIMEOUT $RUNG_ID, reconnect and read $BOX_R/$RUNG_ID-arm.log"
fi

echo "=== pulling receipts ==="
scp -q "$BOX:$BOX_R/${RUNG_ID}-*" "$RECEIPTS/" 2>/dev/null || true
echo "=== window $RUNG_ID closed $(date -u +%H:%M:%SZ) ==="
