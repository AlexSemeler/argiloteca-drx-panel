#!/usr/bin/env bash
set -euo pipefail

# Indexa uma pasta curada de CIFs para o painel DRX da Argiloteca.
# Nao copia CIFs para dentro da Argiloteca; o manifesto guarda caminho, hash,
# picos simulados via pymatgen e proveniencia.

WORKSPACE="${WORKSPACE:-/home/invenio/invenio-project}"
ARGILOTECA_LOCAL="${ARGILOTECA_LOCAL:-$WORKSPACE/argiloteca-local}"
ARGILOTECA_APP="${ARGILOTECA_APP:-$ARGILOTECA_LOCAL/app}"
APP_PYTHON="${APP_PYTHON:-$ARGILOTECA_LOCAL/venvs/app-py310-l3/bin/python}"
SCIENCE_PYTHON="${SCIENCE_PYTHON:-$ARGILOTECA_LOCAL/venvs/drx-science-py310/bin/python}"

DEFAULT_ASE_CIFS="/home/invenio/difract/.venvs/diffractgpt_drx/lib/python3.10/site-packages/ase/test/testdata/minerals"
CIF_SOURCE_DIR="${CIF_SOURCE_DIR:-$DEFAULT_ASE_CIFS}"
CIF_COD_INDEX="${CIF_COD_INDEX:-$ARGILOTECA_LOCAL/instance/argiloteca_drx_references/cif_cod_reference_index.json}"
SOURCE="${SOURCE:-COD}"
MAX_FILES="${MAX_FILES:-1000}"
MAX_PEAKS="${MAX_PEAKS:-80}"
WAVELENGTH="${WAVELENGTH:-CuKa}"
RESTART_ARGILOTECA="${RESTART_ARGILOTECA:-0}"
CHECK_API="${CHECK_API:-1}"
BASE_URL="${BASE_URL:-http://127.0.0.1:5000}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-90}"

log() {
  printf '\n[%s] %s\n' "$(date -Is)" "$*"
}

fail() {
  printf '\n[ERRO] %s\n' "$*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "$2 nao encontrado: $1"
}

require_dir() {
  [[ -d "$1" ]] || fail "$2 nao encontrado: $1"
}

require_executable() {
  [[ -x "$1" ]] || fail "$2 nao executavel/encontrado: $1"
}

wait_api() {
  local deadline=$((SECONDS + STARTUP_TIMEOUT_SECONDS))
  local status="000"
  while (( SECONDS < deadline )); do
    status="$(curl -fsS -o /tmp/argiloteca_health.html -w '%{http_code}' "$BASE_URL/" 2>/dev/null || true)"
    [[ "$status" == "200" ]] && return 0
    sleep 2
  done
  return 1
}

main() {
  cat <<EOF
Configuracao CIF/COD:
  CIF_SOURCE_DIR=$CIF_SOURCE_DIR
  CIF_COD_INDEX=$CIF_COD_INDEX
  SOURCE=$SOURCE
  MAX_FILES=$MAX_FILES
  MAX_PEAKS=$MAX_PEAKS
  WAVELENGTH=$WAVELENGTH
EOF

  require_dir "$CIF_SOURCE_DIR" "pasta CIF"
  require_executable "$APP_PYTHON" "Python da Argiloteca"
  require_executable "$SCIENCE_PYTHON" "Python cientifico"
  require_file "$ARGILOTECA_APP/argiloteca_custom/scripts/build_cif_cod_reference_index.py" "indexador CIF/COD"
  require_file "$ARGILOTECA_APP/argiloteca_custom/scripts/simulate_cif_xrd_pattern.py" "simulador CIF/pymatgen"
  mkdir -p "$(dirname "$CIF_COD_INDEX")"

  local count
  count="$(find "$CIF_SOURCE_DIR" -type f -iname '*.cif' | wc -l | tr -d ' ')"
  [[ "$count" != "0" ]] || fail "nenhum .cif encontrado em $CIF_SOURCE_DIR"
  log "CIFs encontrados: $count"

  "$APP_PYTHON" "$ARGILOTECA_APP/argiloteca_custom/scripts/build_cif_cod_reference_index.py" \
    --input-dir "$CIF_SOURCE_DIR" \
    --output "$CIF_COD_INDEX" \
    --source "$SOURCE" \
    --engine-python "$SCIENCE_PYTHON" \
    --simulator "$ARGILOTECA_APP/argiloteca_custom/scripts/simulate_cif_xrd_pattern.py" \
    --wavelength "$WAVELENGTH" \
    --max-files "$MAX_FILES" \
    --max-peaks "$MAX_PEAKS"

  log "Resumo do manifesto"
  "$APP_PYTHON" - "$CIF_COD_INDEX" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
refs = payload.get("references") or []
print(json.dumps({
    "schema_version": payload.get("schema_version"),
    "source_dir": payload.get("source_dir"),
    "references": len(refs),
    "warnings": len(payload.get("warnings") or []),
    "first_reference": refs[0] if refs else None,
}, ensure_ascii=False, indent=2)[:4000])
PY

  if [[ "$RESTART_ARGILOTECA" == "1" ]]; then
    require_file "$WORKSPACE/iniciar_argiloteca.sh" "script iniciar_argiloteca"
    log "Reiniciando Argiloteca"
    (cd "$WORKSPACE" && setsid ./iniciar_argiloteca.sh > /tmp/argiloteca_restart.log 2>&1 < /dev/null &)
    wait_api || fail "Argiloteca nao respondeu em $BASE_URL apos restart"
  fi

  if [[ "$CHECK_API" == "1" ]]; then
    if ! wait_api; then
      printf '[AVISO] Argiloteca nao esta respondendo em %s; manifesto foi gerado, mas API nao foi checada.\n' "$BASE_URL" >&2
      exit 0
    fi
    log "Consultando API CIF/COD"
    curl -fsS "$BASE_URL/api/argiloteca/drx/references?source=COD&limit=5"
  fi

  log "Concluido. Manifesto: $CIF_COD_INDEX"
}

main "$@"
