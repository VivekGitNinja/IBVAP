#!/usr/bin/env python3
"""Start IBVAP backend as a detached daemon."""
import os, sys, signal

# Double-fork to fully detach
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

os.chdir('/Users/vivek/Downloads/ibvap')
sys.path.insert(0, '.')
os.environ['PYTHONPATH'] = '.'

import uvicorn
uvicorn.run('backend.app.main:app', host='0.0.0.0', port=8001, log_level='info')
