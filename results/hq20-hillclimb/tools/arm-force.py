import os, signal, subprocess, time
out = subprocess.run(["ps","-eo","pid,args"],capture_output=True,text=True).stdout
pids = []
for line in out.splitlines():
    pid, _, args = line.strip().partition(" ")
    if "arm-run.sh" in args and "tailscaled" not in args and "arm-force" not in args:
        pids.append(int(pid))
for p in pids:
    try: os.kill(p, signal.SIGKILL)
    except Exception as e: print("fail", p, e)
print("sigkilled:", pids or "none")
time.sleep(2)
import shutil, os.path
for path in ("/tmp/hillclimb-arm.lock",):
    shutil.rmtree(path, ignore_errors=True)
print("lock cleared:", not os.path.exists("/tmp/hillclimb-arm.lock"))
