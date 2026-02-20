#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"

BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
MONGO_PORT="${MONGO_PORT:-27017}"

stop_by_pidfile() {
  local name="$1"
  local pidfile="$2"

  if [[ ! -f "$pidfile" ]]; then
    echo "[skip] $name pid file not found"
    return
  fi

  local pid
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    echo "[warn] $name pid file was empty"
    rm -f "$pidfile"
    return
  fi

  if ! kill -0 "$pid" >/dev/null 2>&1; then
    echo "[skip] $name process $pid is not running"
    rm -f "$pidfile"
    return
  fi

  kill "$pid" >/dev/null 2>&1 || true
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "[ok] Stopped $name (pid $pid)"
      rm -f "$pidfile"
      return
    fi
    sleep 0.25
  done

  kill -9 "$pid" >/dev/null 2>&1 || true
  rm -f "$pidfile"
  echo "[warn] Force-stopped $name (pid $pid)"
}

stop_by_port() {
  local name="$1"
  local port="$2"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN -n -P 2>/dev/null || true)"

  if [[ -z "$pids" ]]; then
    return
  fi

  for pid in $pids; do
    kill "$pid" >/dev/null 2>&1 || true
    for _ in $(seq 1 20); do
      if ! kill -0 "$pid" >/dev/null 2>&1; then
        break
      fi
      sleep 0.1
    done
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
      echo "[warn] Force-stopped $name on port $port (pid $pid)"
    else
      echo "[ok] Stopped $name on port $port (pid $pid)"
    fi
  done
}

echo "[info] Stopping local stack..."
stop_by_pidfile "Frontend" "$RUN_DIR/frontend.pid"
stop_by_pidfile "Backend" "$RUN_DIR/backend.pid"
stop_by_pidfile "MongoDB" "$RUN_DIR/mongo.pid"

stop_by_port "Frontend" "$FRONTEND_PORT"
stop_by_port "Backend" "$BACKEND_PORT"
stop_by_port "MongoDB" "$MONGO_PORT"

if lsof -iTCP:"$FRONTEND_PORT" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "[note] Port $FRONTEND_PORT still in use."
fi
if lsof -iTCP:"$BACKEND_PORT" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "[note] Port $BACKEND_PORT still in use."
fi
if lsof -iTCP:"$MONGO_PORT" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "[note] Port $MONGO_PORT still in use."
fi

echo "[done] Stop command finished."
