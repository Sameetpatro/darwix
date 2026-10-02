#!/usr/bin/env bash
# =============================================================================
# Darwix Voice Agent & Copilot Server Stopper
# =============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.server.pid"

STOPPED=0

# 1. Kill process recorded in PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "[INFO] Terminating server process PID $PID..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        # Force kill if still lingering
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null || true
        fi
        STOPPED=1
    fi
    rm -f "$PID_FILE"
fi

# 2. Check and terminate any process still occupying port 8000
PORT_PIDS=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$PORT_PIDS" ]; then
    echo "[INFO] Freeing port 8000 (Killing PIDs: $PORT_PIDS)..."
    for P in $PORT_PIDS; do
        kill "$P" 2>/dev/null || true
    done
    sleep 1
    # Force kill any lingering
    PORT_PIDS_REMAINING=$(lsof -ti:8000 2>/dev/null || true)
    if [ -n "$PORT_PIDS_REMAINING" ]; then
        for P in $PORT_PIDS_REMAINING; do
            kill -9 "$P" 2>/dev/null || true
        done
    fi
    STOPPED=1
fi

if [ "$STOPPED" -eq 1 ]; then
    echo "[SUCCESS] Darwix Server stopped. Port 8000 is now free."
else
    echo "[INFO] No active Darwix server was running on port 8000."
fi
