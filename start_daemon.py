"""Start IBVAP backend as a proper daemon process."""
import os
import sys
import signal

# Double-fork to detach from terminal
if os.fork() > 0:
    sys.exit(0)

os.setsid()

if os.fork() > 0:
    sys.exit(0)

# Redirect stdio
sys.stdin = open(os.devnull, 'r')
sys.stdout = open('/tmp/ibvap_out.log', 'a')
sys.stderr = sys.stdout

# Write PID
with open('/tmp/ibvap.pid', 'w') as f:
    f.write(str(os.getpid()))

# Change to project directory
os.chdir('/Users/vivek/Downloads/ibvap')

# Set environment
sys.path.insert(0, '.')
os.environ['PYTHONPATH'] = '.'

# Start uvicorn
import uvicorn
uvicorn.run('backend.app.main:app', host='0.0.0.0', port=8001, log_level='info')
