#!/bin/bash
# Ladder arm scripts generator and runner for h56.
# Each attempt:
# 1. Freeze Mac pid 34846 (kill -STOP 34846)
# 2. Stop systemd watchdog service (systemctl --user stop llama-watchdog.service)
# 3. Kill running llama-server
# 4. Update /home/jamie/llama/llama-serve.sh
# 5. Start watchdog (systemctl --user start llama-watchdog.service)
# 6. Wait for /health ok and verify ps cmdline
# 7. Unfreeze Mac pid 34846 (kill -CONT 34846)
# 8. Run 33k fill point (n=3) + fresh point (n=3) with idle gate
echo "Runbook loaded."
