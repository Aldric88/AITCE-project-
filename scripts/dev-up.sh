#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$RUN_DIR/logs"
ENV_MONGO_DBPATH="${MONGO_DBPATH:-}"

MONGO_HOST="${MONGO_HOST:-127.0.0.1}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DBPATH="$RUN_DIR/mongodb"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

JWT_SECRET_KEY="${JWT_SECRET_KEY:-dev-local-secret}"
MODERATION_AI_MODE="${MODERATION_AI_MODE:-rules}"

mkdir -p "$LOG_DIR" "$MONGO_DBPATH"

if [[ -n "$ENV_MONGO_DBPATH" && "$ENV_MONGO_DBPATH" != "$RUN_DIR/mongodb" ]]; then
  echo "[note] Ignoring external MONGO_DBPATH. Using fixed path: $RUN_DIR/mongodb"
fi

port_open() {
  lsof -iTCP:"$1" -sTCP:LISTEN -n -P >/dev/null 2>&1
}

wait_for_port() {
  local port="$1"
  local name="$2"
  for _ in $(seq 1 60); do
    if port_open "$port"; then
      echo "[ok] $name is listening on port $port"
      return 0
    fi
    sleep 0.25
  done
  echo "[error] $name did not start on port $port. Check $LOG_DIR/$3"
  return 1
}

start_mongo() {
  if port_open "$MONGO_PORT"; then
    echo "[skip] MongoDB already running on $MONGO_HOST:$MONGO_PORT"
    return
  fi
  if ! command -v mongod >/dev/null 2>&1; then
    echo "[error] mongod not found. Install MongoDB first."
    exit 1
  fi
  nohup mongod \
    --dbpath "$MONGO_DBPATH" \
    --bind_ip "$MONGO_HOST" \
    --port "$MONGO_PORT" \
    >"$LOG_DIR/mongo.log" 2>&1 &
  echo "$!" >"$RUN_DIR/mongo.pid"
  wait_for_port "$MONGO_PORT" "MongoDB" "mongo.log"
}

start_backend() {
  if port_open "$BACKEND_PORT"; then
    echo "[skip] Backend already running on $BACKEND_HOST:$BACKEND_PORT"
    return
  fi
  local uvicorn_bin=""
  if [[ -x "$ROOT_DIR/backend/.venv/bin/uvicorn" ]]; then
    uvicorn_bin="$ROOT_DIR/backend/.venv/bin/uvicorn"
  elif command -v uvicorn >/dev/null 2>&1; then
    uvicorn_bin="$(command -v uvicorn)"
  else
    echo "[error] uvicorn not found. Install backend dependencies first."
    exit 1
  fi
  (
    cd "$ROOT_DIR/backend"
    JWT_SECRET_KEY="$JWT_SECRET_KEY" MODERATION_AI_MODE="$MODERATION_AI_MODE" \
      nohup "$uvicorn_bin" app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
      >"$LOG_DIR/backend.log" 2>&1 &
    echo "$!" >"$RUN_DIR/backend.pid"
  )
  wait_for_port "$BACKEND_PORT" "Backend" "backend.log"
}

start_frontend() {
  if port_open "$FRONTEND_PORT"; then
    echo "[skip] Frontend already running on $FRONTEND_HOST:$FRONTEND_PORT"
    return
  fi
  local vite_bin=""
  if [[ -x "$ROOT_DIR/notes-frontend/node_modules/.bin/vite" ]]; then
    vite_bin="$ROOT_DIR/notes-frontend/node_modules/.bin/vite"
  elif command -v vite >/dev/null 2>&1; then
    vite_bin="$(command -v vite)"
  else
    echo "[error] Vite binary not found. Run npm install in notes-frontend first."
    exit 1
  fi
  (
    cd "$ROOT_DIR/notes-frontend"
    nohup "$vite_bin" --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
      >"$LOG_DIR/frontend.log" 2>&1 &
    echo "$!" >"$RUN_DIR/frontend.pid"
  )
  wait_for_port "$FRONTEND_PORT" "Frontend" "frontend.log"
}

echo "[info] Starting local stack..."
start_mongo
start_backend
start_frontend

cat <<EOF
[done] Local stack is up.
Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT
Backend:  http://$BACKEND_HOST:$BACKEND_PORT
Docs:     http://$BACKEND_HOST:$BACKEND_PORT/docs

Logs:
- $LOG_DIR/mongo.log
- $LOG_DIR/backend.log
- $LOG_DIR/frontend.log
Mongo data dir: $MONGO_DBPATH

Stop all: npm run dev:down
EOF
