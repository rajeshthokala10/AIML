#!/usr/bin/env bash
# Run AI-Medicine backend and frontend in the background. Ctrl+C stops both.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if present (required so uvicorn and python use project deps)
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

BACKEND_PID=""
FRONTEND_PID=""
BACKEND_LOG="$SCRIPT_DIR/backend.log"
FRONTEND_LOG="$SCRIPT_DIR/frontend.log"

cleanup() {
  echo ""
  echo "Stopping backend and frontend..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  # Kill vite/node children that may keep port 5173
  (lsof -ti :5173 2>/dev/null | xargs kill 2>/dev/null) || true
  (lsof -ti :8000 2>/dev/null | xargs kill 2>/dev/null) || true
  exit 0
}

trap cleanup SIGINT SIGTERM

# Use project Python so uvicorn and deps are correct
PYTHON_CMD="${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/python}"
PYTHON_CMD="${PYTHON_CMD:-python}"

echo "Starting backend (FastAPI) on http://127.0.0.1:8000 ..."
"$PYTHON_CMD" -m uvicorn api:app --port 8000 --host 127.0.0.1 >> "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo "Starting frontend (Vite) on http://localhost:5173 ..."
# Run Vite with a pseudo-TTY so it starts correctly (Vite can hang without TTY when run in background)
if command -v script >/dev/null 2>&1; then
  (cd frontend && script -q /dev/null npm run dev) >> "$FRONTEND_LOG" 2>&1 &
else
  (cd frontend && npm run dev) >> "$FRONTEND_LOG" 2>&1 &
fi
FRONTEND_PID=$!

echo "Waiting for servers to bind (3s)..."
sleep 3

# Check if ports are in use
BACKEND_UP=""
FRONTEND_UP=""
command -v lsof >/dev/null 2>&1 && {
  lsof -i :8000 -sTCP:LISTEN -t >/dev/null 2>&1 && BACKEND_UP=1
  lsof -i :5173 -sTCP:LISTEN -t >/dev/null 2>&1 && FRONTEND_UP=1
}

echo ""
echo "----------------------------------------"
echo "  Backend:  http://127.0.0.1:8000"
echo "  Swagger:  http://127.0.0.1:8000/docs"
echo "  Frontend: http://localhost:5173"
echo "----------------------------------------"
if [ -n "$BACKEND_UP" ] && [ -n "$FRONTEND_UP" ]; then
  echo "  Both servers are up."
elif [ -n "$BACKEND_UP" ]; then
  echo "  Backend is up. Frontend may still be starting (check frontend.log)."
elif [ -n "$FRONTEND_UP" ]; then
  echo "  Frontend is up. Backend may have failed (check backend.log)."
else
  echo "  Servers may still be starting. If URLs fail, check backend.log and frontend.log."
fi
echo "  Logs: backend.log, frontend.log"
echo "----------------------------------------"
if [ -s "$FRONTEND_LOG" ]; then
  echo "Frontend log (last 20 lines):"
  tail -20 "$FRONTEND_LOG"
  echo "----------------------------------------"
fi
echo "Press Ctrl+C to stop both."
echo ""

wait
