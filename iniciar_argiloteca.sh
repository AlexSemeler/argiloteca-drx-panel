#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/invenio/invenio-project/argiloteca-local"
COMPOSE_FILE="$ROOT/compose/docker-compose.local.yml"
ENV_FILE="$ROOT/secrets/l3-local.env"
APP_DIR="$ROOT/app"
INVENIO_BIN="$ROOT/venvs/app-py310-l3/bin/invenio"
HOST="127.0.0.1"
PORT="5000"

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "Arquivo nao encontrado: $1" >&2
    exit 1
  fi
}

require_dir() {
  if [[ ! -d "$1" ]]; then
    echo "Diretorio nao encontrado: $1" >&2
    exit 1
  fi
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local attempts="${3:-30}"

  echo "Aguardando $label..."
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$label OK"
      return 0
    fi
    sleep 2
  done

  echo "Aviso: $label ainda nao respondeu em $url" >&2
}

port_pids() {
  ss -ltnp "sport = :$PORT" 2>/dev/null \
    | sed -nE 's/.*pid=([0-9]+).*/\1/p' \
    | sort -u
}

free_port() {
  local pids=()
  local pid

  mapfile -t pids < <(port_pids)

  if [[ "${#pids[@]}" -eq 0 ]]; then
    return 0
  fi

  echo "Porta $PORT em uso. Parando PID(s): ${pids[*]}"

  for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
    fi
  done

  for _ in $(seq 1 10); do
    mapfile -t pids < <(port_pids)
    if [[ "${#pids[@]}" -eq 0 ]]; then
      echo "Porta $PORT liberada."
      return 0
    fi
    sleep 1
  done

  echo "PID(s) ainda usando a porta $PORT. Forcando parada: ${pids[*]}"
  for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid"
    fi
  done

  for _ in $(seq 1 5); do
    mapfile -t pids < <(port_pids)
    if [[ "${#pids[@]}" -eq 0 ]]; then
      echo "Porta $PORT liberada."
      return 0
    fi
    sleep 1
  done

  echo "Nao foi possivel liberar a porta $PORT. PID(s): ${pids[*]}" >&2
  exit 1
}

require_file "$COMPOSE_FILE"
require_file "$ENV_FILE"
require_file "$INVENIO_BIN"
require_dir "$APP_DIR"

echo "Subindo servicos da Argiloteca..."
docker compose -f "$COMPOSE_FILE" up -d

wait_for_http "http://127.0.0.1:19200/_cluster/health" "OpenSearch local" 45

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

cd "$APP_DIR"

free_port

echo "Iniciando Argiloteca em http://$HOST:$PORT"
exec "$INVENIO_BIN" run -h "$HOST" -p "$PORT"
