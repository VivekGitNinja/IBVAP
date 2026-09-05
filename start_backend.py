#!/usr/bin/env python3
"""Start IBVAP backend as a daemon process."""
import subprocess, sys, os, time, signal

PID_FILE = "/tmp/ibvap_backend.pid"
LOG_FILE = "/tmp/ibvap_backend.log"

# Kill old process
if os.path.exists(PID_FILE):
    with open(PID_FILE) as f:
        old_pid = int(f.read().strip())
    try:
        os.kill(old_pid, signal.SIGKILL)
        time.sleep(0.5)
    except (ProcessLookupError, PermissionError):
        pass

# Clean up
for f in [PID_FILE, "/tmp/ibvap.db"]:
    try: os.remove(f)
    except FileNotFoundError: pass

# Start backend using double-fork daemonization
pid = os.fork()
if pid > 0:
    # Parent: wait briefly and exit
    time.sleep(4)
    # Check if backend is up
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://127.0.0.1:8001/api/v1/health", timeout=3)
        print(f"✅ Backend is LIVE at http://127.0.0.1:8001")
        print(resp.read().decode()[:200])
    except Exception as e:
        print(f"⚠️ Backend may still be starting: {e}")
    sys.exit(0)

# Child: become session leader
os.setsid()
pid2 = os.fork()
if pid2 > 0:
    sys.exit(0)

# Grandchild: write PID and exec uvicorn
with open(PID_FILE, "w") as f:
    f.write(str(os.getpid()))

repo_dir = "/Users/vivek/Downloads/ibvap"
os.chdir(repo_dir)
sys.path.insert(0, repo_dir)

venv_py = os.path.join(repo_dir, ".venv", "bin", "python3")
py_bin = venv_py if os.path.exists(venv_py) else sys.executable

# Redirect stdout/stderr to log file
log_fd = open(LOG_FILE, "w")
os.dup2(log_fd.fileno(), 1)
os.dup2(log_fd.fileno(), 2)

os.execvp(py_bin, [py_bin, "-m", "uvicorn", 
    "backend.app.main:app", "--host", "0.0.0.0", "--port", "8001"])
