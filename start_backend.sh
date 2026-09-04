#!/bin/bash
cd /Users/vivek/Downloads/ibvap
source .venv/bin/activate
export PYTHONPATH=.
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 &
echo "IBVAP backend started on port 8080"
