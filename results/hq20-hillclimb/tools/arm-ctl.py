import os, signal, subprocess, sys, time
action = sys.argv[1] if len(sys.argv) > 1 else "status"
out = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout
runners = []
for line in out.splitlines():
    pid, _, args = line.strip().partition(" ")
    if "arm-run.sh" in args and "tailscaled" not in args and "arm-ctl" not in args:
        runners.append((pid, args[:80]))
if action == "kill":
    for pid, _ in runners:
        os.kill(int(pid), signal.SIGTERM)
    print("sigterm sent to", [p for p, _ in runners] or "none")
    time.sleep(10)
    out2 = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout
    left = [l.split()[0] for l in out2.splitlines() if "arm-run.sh" in l and "tailscaled" not in l and "arm-ctl" not in l]
    print("still running:", left or "none")
else:
    print("runners:", runners or "none")
