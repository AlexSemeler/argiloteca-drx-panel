#!/usr/bin/env bash
set -euo pipefail

# Pipeline Linux para:
# 1) reclassificar RAWs DRX;
# 2) rodar pacote experimental DiffractGPT/JARVIS em ambiente isolado;
# 3) reconstruir o indice neural auxiliar;
# 4) reiniciar/validar o painel Argiloteca local.
#
# Politica cientifica: DiffractGPT, XRDNet e evidencias neurais permanecem
# auxiliares/experimentais. Este script nao promove estrutura gerada nem
# predicao neural a identificacao mineralogica confirmatoria.

WORKSPACE="${WORKSPACE:-/home/invenio/invenio-project}"
ARGILOTECA_LOCAL="${ARGILOTECA_LOCAL:-$WORKSPACE/argiloteca-local}"
ARGILOTECA_APP="${ARGILOTECA_APP:-$ARGILOTECA_LOCAL/app}"
DRX_UPLOAD_REPO="${DRX_UPLOAD_REPO:-$WORKSPACE/argiloteca-drx-panel-upload}"
DIFRACT_DIR="${DIFRACT_DIR:-/home/invenio/difract}"

RAW_DIR="${RAW_DIR:-$ARGILOTECA_LOCAL/data/drx/raw-classificados}"
DRX_OUT_DIR="${DRX_OUT_DIR:-$ARGILOTECA_LOCAL/data/drx/saida_argiloteca_drx}"
VOCAB_JSON="${VOCAB_JSON:-$DRX_OUT_DIR/webmineral_argilominerais_vocabulario.json}"
TREATMENT_JSON="${TREATMENT_JSON:-$DRX_OUT_DIR/classificacao_tratamento_raw.json}"
METRICS_OUT="${METRICS_OUT:-$ARGILOTECA_LOCAL/reports/drx_panel_metrics.json}"

APP_PYTHON="${APP_PYTHON:-$ARGILOTECA_LOCAL/venvs/app-py310-l3/bin/python}"
DIFRACT_PYTHON="${DIFRACT_PYTHON:-$DIFRACT_DIR/.venvs/diffractgpt_drx/bin/python}"

DATE_TAG="${DATE_TAG:-$(date +%Y%m%d)}"
TOP_CANDIDATES="${TOP_CANDIDATES:-8}"
BASE_URL="${BASE_URL:-http://127.0.0.1:5000}"

# Controles operacionais.
RUN_RECLASSIFICATION="${RUN_RECLASSIFICATION:-1}"
RUN_DIFRACTGPT="${RUN_DIFRACTGPT:-1}"
STRICT_DIFRACTGPT="${STRICT_DIFRACTGPT:-0}"
ALLOW_HF_NETWORK="${ALLOW_HF_NETWORK:-0}"
ALLOW_JARVIS_DOWNLOAD="${ALLOW_JARVIS_DOWNLOAD:-0}"
SMOKE_TIMEOUT="${SMOKE_TIMEOUT:-300}"
BUILD_NEURAL_INDEX="${BUILD_NEURAL_INDEX:-1}"
RUN_NGC_RECLASSIFICATION="${RUN_NGC_RECLASSIFICATION:-1}"
RUN_DIFRACT_NGC_ADAPTER="${RUN_DIFRACT_NGC_ADAPTER:-1}"
VALIDATE_NGC_INTERPRETATION="${VALIDATE_NGC_INTERPRETATION:-1}"
RESTART_ARGILOTECA="${RESTART_ARGILOTECA:-1}"
CHECK_API="${CHECK_API:-1}"
STRICT_API_CHECK="${STRICT_API_CHECK:-0}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-90}"

NEURAL_SOURCE_DIR="${NEURAL_SOURCE_DIR:-$DIFRACT_DIR/outputs/drx_argilominerais_webmineral_full}"
NEURAL_INDEX_OUT="${NEURAL_INDEX_OUT:-$ARGILOTECA_LOCAL/instance/argiloteca_drx_neural/neural_evidence_index.json}"
NGC_PIPELINE_SCRIPT="${NGC_PIPELINE_SCRIPT:-$WORKSPACE/treinar_difract_ngc_argiloteca.sh}"
NGC_GROUP_JSON="${NGC_GROUP_JSON:-$DRX_OUT_DIR/classificacao_mineralogica_ngc_groups.json}"
NGC_GROUP_CSV="${NGC_GROUP_CSV:-$DRX_OUT_DIR/classificacao_mineralogica_ngc_groups.csv}"
NGC_GROUP_LEGACY_DIR="${NGC_GROUP_LEGACY_DIR:-$ARGILOTECA_LOCAL/povoamento/visualizacao-drx/saida_argiloteca_drx}"
NGC_GROUP_LEGACY_JSON="$NGC_GROUP_LEGACY_DIR/classificacao_mineralogica_ngc_groups.json"
NGC_GROUP_LEGACY_CSV="$NGC_GROUP_LEGACY_DIR/classificacao_mineralogica_ngc_groups.csv"
NGC_RULES_JSON="${NGC_RULES_JSON:-$ARGILOTECA_APP/argiloteca_custom/argiloteca/data/diagnostic_rules_ngc.json}"
NGC_WORKFLOW_SERVICE="${NGC_WORKFLOW_SERVICE:-$ARGILOTECA_APP/argiloteca_custom/argiloteca/services/drx_ngc_workflow.py}"
NGC_DOC_PATH="${NGC_DOC_PATH:-$ARGILOTECA_LOCAL/docs/drx-ngc-interpretation.md}"

log() {
  printf '\n[%s] %s\n' "$(date -Is)" "$*"
}

warn() {
  printf '\n[AVISO] %s\n' "$*" >&2
}

fail() {
  printf '\n[ERRO] %s\n' "$*" >&2
  exit 1
}

require_file() {
  local path="$1"
  local label="$2"
  [[ -f "$path" ]] || fail "$label nao encontrado: $path"
}

require_dir() {
  local path="$1"
  local label="$2"
  [[ -d "$path" ]] || fail "$label nao encontrado: $path"
}

require_executable() {
  local path="$1"
  local label="$2"
  [[ -x "$path" ]] || fail "$label nao executavel/encontrado: $path"
}

python_path() {
  printf '%s:%s:%s' "$ARGILOTECA_APP" "$ARGILOTECA_APP/argiloteca_custom" "$WORKSPACE"
}

print_config() {
  cat <<EOF
Configuracao:
  WORKSPACE=$WORKSPACE
  ARGILOTECA_LOCAL=$ARGILOTECA_LOCAL
  RAW_DIR=$RAW_DIR
  DRX_OUT_DIR=$DRX_OUT_DIR
  VOCAB_JSON=$VOCAB_JSON
  DIFRACT_DIR=$DIFRACT_DIR
  DATE_TAG=$DATE_TAG
  BASE_URL=$BASE_URL
  RUN_RECLASSIFICATION=$RUN_RECLASSIFICATION
  RUN_DIFRACTGPT=$RUN_DIFRACTGPT
  STRICT_DIFRACTGPT=$STRICT_DIFRACTGPT
  ALLOW_HF_NETWORK=$ALLOW_HF_NETWORK
  ALLOW_JARVIS_DOWNLOAD=$ALLOW_JARVIS_DOWNLOAD
  BUILD_NEURAL_INDEX=$BUILD_NEURAL_INDEX
  RUN_NGC_RECLASSIFICATION=$RUN_NGC_RECLASSIFICATION
  RUN_DIFRACT_NGC_ADAPTER=$RUN_DIFRACT_NGC_ADAPTER
  VALIDATE_NGC_INTERPRETATION=$VALIDATE_NGC_INTERPRETATION
  NGC_RULES_JSON=$NGC_RULES_JSON
  RESTART_ARGILOTECA=$RESTART_ARGILOTECA
  CHECK_API=$CHECK_API
  STRICT_API_CHECK=$STRICT_API_CHECK
EOF
}

validate_ngc_interpretation_layer() {
  log "Validando camada de interpretacao N/G/C"
  require_file "$NGC_RULES_JSON" "regras diagnosticas N/G/C"
  require_file "$NGC_WORKFLOW_SERVICE" "servico de workflow N/G/C"
  require_executable "$APP_PYTHON" "Python da Argiloteca"

  "$APP_PYTHON" - "$NGC_RULES_JSON" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
rules = payload.get("rules") or []
required = {
    "kaolin_group_ngc",
    "chlorite_group_ngc",
    "smectite_group_ngc",
    "illite_mica_ngc",
    "vermiculite_group_ngc",
    "mixed_layer_ngc",
}
found = {row.get("rule_id") for row in rules if isinstance(row, dict)}
missing = sorted(required - found)
if missing:
    raise SystemExit("regras obrigatorias ausentes: " + ", ".join(missing))
print(json.dumps({
    "rules_path": str(path),
    "version": payload.get("version"),
    "rule_count": len(rules),
    "required_rules_ok": True,
    "interpretation_policy": payload.get("interpretation_policy"),
}, ensure_ascii=False, indent=2))
PY

  PYTHONPATH="$(python_path)" "$APP_PYTHON" -m py_compile "$NGC_WORKFLOW_SERVICE"

  PYTHONPATH="$(python_path)" "$APP_PYTHON" - <<'PY'
from argiloteca.services.drx_ngc_workflow import build_ngc_workflow

payload = build_ngc_workflow([
    {"filename": "SMOKE (N).raw", "sample_base": "SMOKE", "preparation": "natural", "peaks": [{"d": 15.0, "i_abs": 80}]},
    {"filename": "SMOKE (G).raw", "sample_base": "SMOKE", "preparation": "glicolado", "peaks": [{"d": 17.0, "i_abs": 100}]},
    {"filename": "SMOKE (C).raw", "sample_base": "SMOKE", "preparation": "calcinado", "peaks": [{"d": 10.0, "i_abs": 70}]},
])
group = payload["groups"][0]
clay = group.get("clay_interpretation") or {}
candidates = {row.get("candidateId"): row for row in clay.get("candidates") or []}
smectite = candidates.get("smectite_group") or {}
if smectite.get("status") != "provável" or (smectite.get("score") or 0) < 0.8:
    raise SystemExit("smoke N/G/C falhou para esmectita")
print("smoke-ngc-ok", smectite.get("candidateLabelPt"), smectite.get("score"), smectite.get("status"))
PY

  if [[ -f "$NGC_DOC_PATH" ]]; then
    log "Documentacao N/G/C disponivel: $NGC_DOC_PATH"
  else
    warn "Documentacao N/G/C nao encontrada: $NGC_DOC_PATH"
  fi
}

run_reclassification() {
  log "Reclassificando RAWs DRX"
  require_dir "$DRX_UPLOAD_REPO" "repo de scripts DRX"
  require_dir "$RAW_DIR" "pasta de RAWs"
  require_file "$VOCAB_JSON" "vocabulario WebMineral"
  require_executable "$APP_PYTHON" "Python da Argiloteca"
  mkdir -p "$DRX_OUT_DIR" "$(dirname "$METRICS_OUT")"

  local raw_count
  raw_count="$(find "$RAW_DIR" -type f -iname '*.raw' | wc -l | tr -d ' ')"
  log "RAWs encontrados: $raw_count"

  PYTHONPATH="$(python_path)" \
  INVENIO_INSTANCE_PATH="$ARGILOTECA_LOCAL/instance" \
  "$APP_PYTHON" "$DRX_UPLOAD_REPO/povoamento/drx/classificar_minerais_raw.py" \
    --input "$RAW_DIR" \
    --output-dir "$DRX_OUT_DIR" \
    --cache-referencia "$VOCAB_JSON" \
    --top-candidates "$TOP_CANDIDATES"

  require_file "$DRX_OUT_DIR/classificacao_mineralogica_raw.json" "snapshot mineralogico gerado"
  require_file "$DRX_OUT_DIR/classificacao_mineralogica_resumo.json" "resumo mineralogico gerado"
  require_file "$DRX_OUT_DIR/classificacao_mineralogica_raw.csv" "CSV mineralogico gerado"

  if [[ -f "$TREATMENT_JSON" ]]; then
    log "Gerando metricas do painel DRX"
    PYTHONPATH="$(python_path)" \
    INVENIO_INSTANCE_PATH="$ARGILOTECA_LOCAL/instance" \
    "$APP_PYTHON" "$DRX_UPLOAD_REPO/povoamento/drx/gerar_metricas_painel_drx.py" \
      --raw-snapshot "$DRX_OUT_DIR/classificacao_mineralogica_raw.json" \
      --treatment-snapshot "$TREATMENT_JSON" \
      --output "$METRICS_OUT"
  else
    warn "Snapshot de tratamento nao encontrado; metricas agregadas foram puladas: $TREATMENT_JSON"
  fi
}

run_diffractgpt() {
  log "Rodando DiffractGPT/JARVIS experimental"
  require_dir "$DIFRACT_DIR" "diretorio diffract"
  require_executable "$DIFRACT_PYTHON" "Python isolado DiffractGPT"
  require_file "$DIFRACT_DIR/scripts/diffractgpt_real_argilominerais.py" "script DiffractGPT"

  local args=("--date-tag" "$DATE_TAG" "--smoke-timeout" "$SMOKE_TIMEOUT")
  if [[ "$ALLOW_HF_NETWORK" == "1" ]]; then
    args+=("--allow-hf-network")
  fi
  if [[ "$ALLOW_JARVIS_DOWNLOAD" == "1" ]]; then
    args+=("--allow-jarvis-download")
  else
    args+=("--skip-jarvis-download")
  fi

  set +e
  (
    cd "$DIFRACT_DIR"
    "$DIFRACT_PYTHON" scripts/diffractgpt_real_argilominerais.py "${args[@]}"
  )
  local status=$?
  set -e

  local out_dir="$DIFRACT_DIR/outputs/diffractgpt_real_argilominerais_$DATE_TAG"
  local gate="$out_dir/09_panel_integration_review_gate.json"
  if [[ $status -ne 0 ]]; then
    warn "DiffractGPT terminou com status $status. Consulte: $out_dir"
    [[ "$STRICT_DIFRACTGPT" == "1" ]] && exit "$status"
  fi

  if [[ -f "$gate" ]]; then
    log "Gate de integracao DiffractGPT encontrado"
    "$APP_PYTHON" - "$gate" <<'PY'
import json, sys
from pathlib import Path
gate = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(json.dumps({
    "gate": str(sys.argv[1]),
    "integration_allowed": gate.get("integration_allowed"),
    "status": gate.get("status"),
    "policy": gate.get("policy") or gate.get("interpretation_policy"),
}, ensure_ascii=False, indent=2))
PY
  else
    warn "Gate de integracao DiffractGPT nao encontrado: $gate"
  fi

  log "DiffractGPT permanece experimental; nada estrutural foi publicado como confirmatorio."
}

build_neural_index() {
  log "Reconstruindo indice neural auxiliar do painel"
  require_file "$ARGILOTECA_APP/argiloteca_custom/scripts/build_drx_neural_evidence_index.py" "script do indice neural"
  require_dir "$NEURAL_SOURCE_DIR" "fonte neural pre-computada"
  mkdir -p "$(dirname "$NEURAL_INDEX_OUT")"

  "$APP_PYTHON" "$ARGILOTECA_APP/argiloteca_custom/scripts/build_drx_neural_evidence_index.py" \
    --source-dir "$NEURAL_SOURCE_DIR" \
    --output "$NEURAL_INDEX_OUT"

  require_file "$NEURAL_INDEX_OUT" "indice neural gerado"
}

sync_ngc_group_index_for_panel() {
  if [[ ! -f "$NGC_GROUP_JSON" ]]; then
    warn "Indice N/G/C nao encontrado para sincronizar com o painel: $NGC_GROUP_JSON"
    return 0
  fi
  mkdir -p "$NGC_GROUP_LEGACY_DIR"
  cp "$NGC_GROUP_JSON" "$NGC_GROUP_LEGACY_JSON"
  if [[ -f "$NGC_GROUP_CSV" ]]; then
    cp "$NGC_GROUP_CSV" "$NGC_GROUP_LEGACY_CSV"
  fi
  log "Indice N/G/C sincronizado para o caminho legado do painel: $NGC_GROUP_LEGACY_JSON"
}

run_ngc_reclassification_and_diffract_adapter() {
  log "Rodando reclassificacao N/G/C e adaptador Diffract auxiliar"
  require_file "$NGC_PIPELINE_SCRIPT" "pipeline N/G/C Diffract"
  require_dir "$RAW_DIR" "pasta de RAWs"
  chmod +x "$NGC_PIPELINE_SCRIPT"

  local build_dataset=1
  local run_training="$RUN_DIFRACT_NGC_ADAPTER"
  local run_inference="$RUN_DIFRACT_NGC_ADAPTER"
  local rebuild_index="$RUN_NGC_RECLASSIFICATION"

  (
    cd "$WORKSPACE"
    DATE_TAG="$DATE_TAG" \
    ARGILOTECA_LOCAL="$ARGILOTECA_LOCAL" \
    DIFRACT_DIR="$DIFRACT_DIR" \
    RAW_DIR="$RAW_DIR" \
    REBUILD_NGC_INDEX="$rebuild_index" \
    BUILD_DATASET="$build_dataset" \
    RUN_TRAINING="$run_training" \
    RUN_INFERENCE="$run_inference" \
    STRICT=0 \
    "$NGC_PIPELINE_SCRIPT"
  )

  require_file "$NGC_GROUP_JSON" "indice N/G/C gerado"
  sync_ngc_group_index_for_panel
}

restart_argiloteca() {
  log "Reiniciando Argiloteca local"
  require_file "$WORKSPACE/iniciar_argiloteca.sh" "script iniciar_argiloteca"
  (
    cd "$WORKSPACE"
    setsid ./iniciar_argiloteca.sh > /tmp/argiloteca_restart.log 2>&1 < /dev/null &
  )
  log "Aguardando Argiloteca responder em $BASE_URL/ por ate ${STARTUP_TIMEOUT_SECONDS}s"
  local deadline=$((SECONDS + STARTUP_TIMEOUT_SECONDS))
  local status="000"
  while (( SECONDS < deadline )); do
    status="$(curl -fsS -o /tmp/argiloteca_health.html -w '%{http_code}' "$BASE_URL/" 2>/dev/null || true)"
    if [[ "$status" == "200" ]]; then
      log "Argiloteca respondeu 200."
      return 0
    fi
    sleep 2
  done
  tail -n 80 /tmp/argiloteca_restart.log >&2 || true
  fail "Argiloteca nao respondeu em ${STARTUP_TIMEOUT_SECONDS}s; ultimo status=$status"
}

check_api() {
  log "Validando API local"
  if ! command -v curl >/dev/null 2>&1; then
    warn "curl nao encontrado; checks de API pulados."
    return 0
  fi

  local api_deadline=$((SECONDS + STARTUP_TIMEOUT_SECONDS))
  local api_ok=0
  while (( SECONDS < api_deadline )); do
    if curl -fsS --connect-timeout 5 --max-time 45 "$BASE_URL/api/argiloteca/drx/raw-snapshot?limit=1" >/tmp/argiloteca_drx_raw_snapshot_check.json 2>/tmp/argiloteca_drx_raw_snapshot_check.err \
      && curl -fsS --connect-timeout 5 --max-time 30 "$BASE_URL/api/argiloteca/drx/references?limit=3" >/tmp/argiloteca_drx_references_check.json 2>/tmp/argiloteca_drx_references_check.err \
      && curl -fsS --connect-timeout 5 --max-time 30 "$BASE_URL/api/argiloteca/drx/runs?limit=1" >/tmp/argiloteca_drx_runs_check.json 2>/tmp/argiloteca_drx_runs_check.err; then
      api_ok=1
      break
    fi
    sleep 2
  done
  if [[ "$api_ok" != "1" ]]; then
    warn "Ultimo erro raw-snapshot: $(cat /tmp/argiloteca_drx_raw_snapshot_check.err 2>/dev/null || true)"
    warn "Ultimo erro references: $(cat /tmp/argiloteca_drx_references_check.err 2>/dev/null || true)"
    warn "Ultimo erro runs: $(cat /tmp/argiloteca_drx_runs_check.err 2>/dev/null || true)"
    if [[ "$STRICT_API_CHECK" == "1" ]]; then
      fail "API DRX nao estabilizou em ${STARTUP_TIMEOUT_SECONDS}s apos o restart."
    fi
    warn "API DRX nao estabilizou em ${STARTUP_TIMEOUT_SECONDS}s; pipeline continuara porque STRICT_API_CHECK=0."
    warn "Valide manualmente depois com: curl -fsS '$BASE_URL/api/argiloteca/drx/raw-snapshot?limit=1'"
    return 0
  fi

  local ngc_check
  local ngc_deadline=$((SECONDS + STARTUP_TIMEOUT_SECONDS))
  ngc_check="0"
  while (( SECONDS < ngc_deadline )); do
    ngc_check="$(curl -fsS --connect-timeout 5 --max-time 45 "$BASE_URL/api/argiloteca/drx/raw-snapshot?q=22-25&limit=20" 2>/tmp/argiloteca_drx_ngc_check.err \
      | "$APP_PYTHON" -c 'import json,sys; p=json.load(sys.stdin); items=p.get("items") or []; print(sum(1 for i in items if i.get("ngc_group_classification")))' \
      || true)"
    [[ "${ngc_check:-0}" -gt 0 ]] && break
    sleep 2
  done
  if [[ "${ngc_check:-0}" -gt 0 ]]; then
    log "Check N/G/C OK: endpoint raw-snapshot entrega ngc_group_classification para 22-25."
  else
    warn "Check N/G/C nao encontrou ngc_group_classification em 22-25; confira se o indice existe e se o servidor foi reiniciado."
  fi

  log "Checks OK. Painel: $BASE_URL/drx/comparacao"
}

main() {
  print_config
  require_dir "$ARGILOTECA_LOCAL" "Argiloteca local"
  require_executable "$APP_PYTHON" "Python da Argiloteca"

  if [[ "$RUN_RECLASSIFICATION" == "1" ]]; then
    run_reclassification
  else
    warn "Reclassificacao pulada por RUN_RECLASSIFICATION=0"
  fi

  if [[ "$RUN_DIFRACTGPT" == "1" ]]; then
    run_diffractgpt
  else
    warn "DiffractGPT pulado por RUN_DIFRACTGPT=0"
  fi

  if [[ "$RUN_NGC_RECLASSIFICATION" == "1" || "$RUN_DIFRACT_NGC_ADAPTER" == "1" ]]; then
    if [[ "$VALIDATE_NGC_INTERPRETATION" == "1" ]]; then
      validate_ngc_interpretation_layer
    else
      warn "Validacao da camada N/G/C pulada por VALIDATE_NGC_INTERPRETATION=0"
    fi
    run_ngc_reclassification_and_diffract_adapter
  else
    warn "Reclassificacao N/G/C e adaptador Diffract pulados."
  fi

  if [[ "$BUILD_NEURAL_INDEX" == "1" ]]; then
    build_neural_index
  else
    warn "Indice neural pulado por BUILD_NEURAL_INDEX=0"
  fi

  if [[ "$RESTART_ARGILOTECA" == "1" ]]; then
    restart_argiloteca
  else
    warn "Restart pulado por RESTART_ARGILOTECA=0"
  fi

  if [[ "$CHECK_API" == "1" ]]; then
    check_api
  else
    warn "Checks de API pulados por CHECK_API=0"
  fi

  log "Concluido."
  cat <<EOF
Artefatos principais:
  Snapshot DRX: $DRX_OUT_DIR/classificacao_mineralogica_raw.json
  Resumo DRX:   $DRX_OUT_DIR/classificacao_mineralogica_resumo.json
  Metricas:     $METRICS_OUT
  N/G/C grupos: $NGC_GROUP_JSON
  N/G/C painel: $NGC_GROUP_LEGACY_JSON
  Regras N/G/C:$NGC_RULES_JSON
  Adaptador N/G/C Diffract: $DIFRACT_DIR/models/argiloteca_ngc_group_adapter_$DATE_TAG
  Indice neural:$NEURAL_INDEX_OUT
  DiffractGPT:  $DIFRACT_DIR/outputs/diffractgpt_real_argilominerais_$DATE_TAG
  Painel:       $BASE_URL/drx/comparacao
EOF
}

main "$@"
