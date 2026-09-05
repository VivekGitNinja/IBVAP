#!/bin/bash
cd /Users/vivek/Downloads/ibvap
source .venv/bin/activate
export PYTHONPATH=.
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 &
echo "IBVAP backend started on port 8001"
