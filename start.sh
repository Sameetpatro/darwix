#!/usr/bin/env bash
# =============================================================================
# Darwix Voice Agent & Copilot Server Launcher
# =============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# 1. Locate the correct Python environment
if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$DIR/.venv/bin/python"
elif [ -n "$VIRTUAL_ENV" ] && [ -f "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "[ERROR] No Python binary found. Please install Python 3.11+."
    exit 1
fi

# Verify uvicorn is installed in this python
if ! "$PYTHON_BIN" -c "import uvicorn" >/dev/null 2>&1; then
    echo "[ERROR] 'uvicorn' is not installed in $PYTHON_BIN."
    echo "[HINT] Run: source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Ensure logs directory exists
mkdir -p logs

PID_FILE="$DIR/.server.pid"
LOG_FILE="$DIR/logs/server.log"

# Check if port 8000 is already in use
PORT_PID=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$PORT_PID" ]; then
    echo "[WARNING] Port 8000 is already in use by PID(s): $PORT_PID"
    echo "[HINT] Run ./stop.sh first if you want to restart."
    exit 0
fi

# Check for foreground flag
if [ "$1" = "-f" ] || [ "$1" = "--foreground" ]; then
    echo "[INFO] Starting Darwix Server in foreground..."
    echo "[INFO] Web Softphone:        http://localhost:8000/"
    echo "[INFO] Copilot Dashboard:     http://localhost:8000/dashboard"
    echo "[INFO] Health Check:          http://localhost:8000/api/health"
    exec "$PYTHON_BIN" start.py
fi

# Default: Start in background
echo "[INFO] Launching Darwix Server in background..."
nohup "$PYTHON_BIN" start.py > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

# Wait a brief moment to ensure startup
sleep 2

# Verify server health
if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
    echo "================================================================="
    echo "  Darwix Server Started Successfully (PID: $SERVER_PID)"
    echo "================================================================="
    echo "  * Softphone UI:        http://localhost:8000/"
    echo "  * Copilot Dashboard:   http://localhost:8000/dashboard"
    echo "  * Health Check:        http://localhost:8000/api/health"
    echo "  * Server Log:          tail -f logs/server.log"
    echo "  * Stop Server:         ./stop.sh"
    echo "================================================================="
else
    # Check if process is still running
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "[INFO] Server is initializing (PID: $SERVER_PID). Tail logs with: tail -f logs/server.log"
    else
        echo "[ERROR] Server failed to start. Last log lines:"
        tail -n 20 "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
fi
