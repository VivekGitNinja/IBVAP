#!/usr/bin/env bash
set -e

echo "╔══════════════════════════════════════════════════╗"
echo "║  IBVAP — Intelligent Border Video Analytics     ║"
echo "║  SIH 2026 • Problem Statement 26187             ║"
echo "╚══════════════════════════════════════════════════╝"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required"
    exit 1
fi

PORT=${PORT:-8001}

echo "[1/4] Ensuring ports $PORT and 5173 are free..."
lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true
sleep 1

# Setup venv if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install dependencies if missing
echo "[2/4] Verifying Python dependencies..."
pip install -q -r backend/requirements.txt 2>/dev/null || true

# Setup env
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || true
fi

echo "[3/4] Starting IBVAP backend on port $PORT..."
PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend startup..."
for i in {1..15}; do
    if curl -s http://127.0.0.1:$PORT/api/v1/status >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# Seed demo data if requested
echo "[4/4] Syncing C4ISR demo intelligence..."
PYTHONPATH=. python -c "
import urllib.request, json
data = json.dumps({}).encode()
req = urllib.request.Request('http://127.0.0.1:$PORT/api/v1/demo/seed/all', data=data, method='POST', headers={'Content-Type': 'application/json'})
try:
    resp = urllib.request.urlopen(req, timeout=5)
    print('Demo data initialized successfully')
except Exception as e:
    print(f'Demo seeding info: {e}')
" 2>/dev/null || true

# Start frontend
FRONTEND_PID=""
if command -v npm &> /dev/null && [ -d "frontend" ]; then
    echo "Starting Vite Frontend Command Center on port 5173..."
    (cd frontend && npm run dev -- --host 0.0.0.0 --port 5173) &
    FRONTEND_PID=$!
fi

echo ""
echo "══════════════════════════════════════════════════"
echo "  ⚡ IBVAP C4ISR Platform is LIVE & OPERATIONAL!"
echo ""
echo "  Command Center: http://localhost:5173"
echo "  FastAPI Direct: http://localhost:$PORT"
echo "  API Docs:       http://localhost:$PORT/docs"
echo "  System Status:  http://localhost:$PORT/api/v1/status"
echo ""
echo "  Default Login:  operator / operator123"
echo "══════════════════════════════════════════════════"
echo "Press Ctrl+C to shut down all services."

cleanup() {
    echo ""
    echo "Shutting down IBVAP Platform services..."
    [ -n "$BACKEND_PID" ] && kill -TERM "$BACKEND_PID" 2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill -TERM "$FRONTEND_PID" 2>/dev/null || true
    lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM
wait
