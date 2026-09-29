#!/bin/bash
# launch-rung.sh <rung-id> — vLLM arm window with a watchdog suppressor.
# The box watchdog script respawns production llama mid-window and fights the
# arm for VRAM; this holds it down for the whole window and lets box-window.sh
# restore it on closeout.
set -u
S=/home/jamie/hq20/hillclimb
RUNG="$1"
WD_SCRIPT=/home/jamie/llama/llama-watchdog.sh

kill_watchdog_script() {
  ps -eo pid,args | awk -v wd="$WD_SCRIPT" 'index($0, "/bin/bash " wd) == 1 { print $1 }' \
    | while read -r p; do [ "$p" != "$$" ] && kill "$p" 2>/dev/null; done
}

rm -rf "$S/$RUNG-samples"
bash "$S/vram-sampler.sh" "$S/$RUNG-samples" &
SP=$!
trap 'kill "$SP" 2>/dev/null' EXIT

(systemctl --user stop llama-watchdog.service 2>/dev/null
 while pgrep -f "box-window.sh $S/$RUNG.env" >/dev/null 2>&1; do
   kill_watchdog_script
   sleep 5
 done) &
SUPP=$!

bash "$S/box-window.sh" "$S/$RUNG.env"
kill "$SUPP" 2>/dev/null
kill "$SP" 2>/dev/null
date -u +%Y-%m-%dT%H:%M:%SZ > "$S/$RUNG-samples/PROBE_DONE"
echo WINDOW_CLOSED
