#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${WORKSPACE:-/home/invenio/invenio-project}"
ARGILOTECA_LOCAL="${ARGILOTECA_LOCAL:-$WORKSPACE/argiloteca-local}"
DIFRACT_DIR="${DIFRACT_DIR:-/home/invenio/difract}"
DATE_TAG="${DATE_TAG:-$(date +%Y%m%d)}"

REBUILD_NGC_INDEX="${REBUILD_NGC_INDEX:-0}"
BUILD_DATASET="${BUILD_DATASET:-1}"
RUN_TRAINING="${RUN_TRAINING:-0}"
RUN_INFERENCE="${RUN_INFERENCE:-0}"
STRICT="${STRICT:-0}"

RAW_DIR="${RAW_DIR:-$ARGILOTECA_LOCAL/data/drx/raw-classificados}"
NGC_SCRIPT="${NGC_SCRIPT:-$ARGILOTECA_LOCAL/app/argiloteca_custom/scripts/batch_ngc_raw_diagnostics.py}"
NGC_INDEX="${NGC_INDEX:-$ARGILOTECA_LOCAL/data/drx/saida_argiloteca_drx/classificacao_mineralogica_ngc_groups.json}"
NGC_INDEX_DIR="$(dirname "$NGC_INDEX")"
NGC_RULES_JSON="${NGC_RULES_JSON:-$ARGILOTECA_LOCAL/app/argiloteca_custom/argiloteca/data/diagnostic_rules_ngc.json}"
NGC_WORKFLOW_SERVICE="${NGC_WORKFLOW_SERVICE:-$ARGILOTECA_LOCAL/app/argiloteca_custom/argiloteca/services/drx_ngc_workflow.py}"

DIFRACT_PY="${DIFRACT_PY:-}"
DATASET_DIR="${DATASET_DIR:-$DIFRACT_DIR/datasets/argiloteca_ngc_training}"
OUTPUT_DIR="${OUTPUT_DIR:-$DIFRACT_DIR/outputs/argiloteca_ngc_training_${DATE_TAG}}"
LOG_DIR="${LOG_DIR:-$DIFRACT_DIR/logs}"
REPORT_DIR="${REPORT_DIR:-$DIFRACT_DIR/reports}"
REPORT_PATH="$REPORT_DIR/RELATORIO_ARGILOTECA_NGC_DIFRACT_${DATE_TAG}.md"
RUN_LOG="$LOG_DIR/argiloteca_ngc_diffract_${DATE_TAG}.log"
NGC_MODEL_DIR="${NGC_MODEL_DIR:-$DIFRACT_DIR/models/argiloteca_ngc_group_adapter_${DATE_TAG}}"

if ! mkdir -p "$LOG_DIR" "$REPORT_DIR" "$OUTPUT_DIR"; then
  printf '[ERRO] Nao foi possivel criar diretorios de saida do Diffract: %s %s %s\n' "$LOG_DIR" "$REPORT_DIR" "$OUTPUT_DIR" >&2
  printf '[ERRO] Verifique permissoes ou ajuste DIFRACT_DIR para um caminho gravavel.\n' >&2
  exit 1
fi

log() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*" | tee -a "$RUN_LOG"
}

warn() {
  printf '[AVISO] %s\n' "$*" | tee -a "$RUN_LOG"
}

fail_or_warn() {
  local message="$1"
  if [[ "$STRICT" == "1" ]]; then
    printf '[ERRO] %s\n' "$message" | tee -a "$RUN_LOG" >&2
    exit 1
  fi
  warn "$message"
}

choose_python() {
  if [[ -n "$DIFRACT_PY" && -x "$DIFRACT_PY" ]]; then
    printf '%s\n' "$DIFRACT_PY"
    return 0
  fi
  for candidate in \
    "$DIFRACT_DIR/.venvs/diffractgpt_drx/bin/python" \
    "$DIFRACT_DIR/.venv/bin/python" \
    "$DIFRACT_DIR/.venvs/drx_ml_tests/bin/python" \
    "$DIFRACT_DIR/.venvs/opxrd_pretrain/bin/python"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  command -v python3
}

PYTHON_BIN="$(choose_python)"
DATASET_BUILDER="$DIFRACT_DIR/scripts/build_argiloteca_ngc_training_dataset.py"
NGC_TRAIN_ADAPTER="$DIFRACT_DIR/scripts/train_argiloteca_ngc_group_adapter.py"
TRAIN_SCRIPT="$DIFRACT_DIR/scripts/train_xrdnet_argilominerais.py"
INFER_SCRIPT="$DIFRACT_DIR/scripts/drx_neural_inference.py"

write_report_header() {
  cat > "$REPORT_PATH" <<MD
# Relatório Argiloteca N/G/C Diffract

- Data: $(date --iso-8601=seconds)
- Política: evidência auxiliar, experimental e não confirmatória.
- Argiloteca: \`$ARGILOTECA_LOCAL\`
- Diffract: \`$DIFRACT_DIR\`
- Índice N/G/C: \`$NGC_INDEX\`
- Regras diagnósticas N/G/C: \`$NGC_RULES_JSON\`
- Dataset: \`$DATASET_DIR\`
- Saída: \`$OUTPUT_DIR\`
- Modelo N/G/C: \`$NGC_MODEL_DIR\`
- Log: \`$RUN_LOG\`

## Execução

MD
}

append_report() {
  printf '%s\n' "$*" >> "$REPORT_PATH"
}

write_report_header

log "Configuracao:"
log "  ARGILOTECA_LOCAL=$ARGILOTECA_LOCAL"
log "  DIFRACT_DIR=$DIFRACT_DIR"
log "  PYTHON_BIN=$PYTHON_BIN"
log "  DATE_TAG=$DATE_TAG"
log "  REBUILD_NGC_INDEX=$REBUILD_NGC_INDEX"
log "  BUILD_DATASET=$BUILD_DATASET"
log "  RUN_TRAINING=$RUN_TRAINING"
log "  RUN_INFERENCE=$RUN_INFERENCE"
log "  STRICT=$STRICT"
log "  NGC_RULES_JSON=$NGC_RULES_JSON"

append_report "- Python: \`$PYTHON_BIN\`"
append_report "- REBUILD_NGC_INDEX=$REBUILD_NGC_INDEX"
append_report "- BUILD_DATASET=$BUILD_DATASET"
append_report "- RUN_TRAINING=$RUN_TRAINING"
append_report "- RUN_INFERENCE=$RUN_INFERENCE"
append_report "- Regras N/G/C: \`$NGC_RULES_JSON\`"
append_report ""

if [[ ! -d "$DIFRACT_DIR" ]]; then
  fail_or_warn "Diretorio Diffract nao encontrado: $DIFRACT_DIR"
  exit 0
fi

if [[ -f "$NGC_RULES_JSON" && -f "$NGC_WORKFLOW_SERVICE" ]]; then
  log "Validando contrato de regras N/G/C antes do dataset"
  "$PYTHON_BIN" - "$NGC_RULES_JSON" <<'PY' 2>&1 | tee -a "$RUN_LOG"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rules = payload.get("rules") or []
required = {"kaolin_group_ngc", "chlorite_group_ngc", "smectite_group_ngc", "illite_mica_ngc", "vermiculite_group_ngc", "mixed_layer_ngc"}
found = {row.get("rule_id") for row in rules if isinstance(row, dict)}
missing = sorted(required - found)
if missing:
    raise SystemExit("regras obrigatorias ausentes: " + ", ".join(missing))
print({"version": payload.get("version"), "rule_count": len(rules), "required_rules_ok": True})
PY
  append_report "- Regras N/G/C validadas antes da geração do dataset."
else
  fail_or_warn "Regras ou serviço N/G/C não encontrados: $NGC_RULES_JSON / $NGC_WORKFLOW_SERVICE"
fi

if [[ "$REBUILD_NGC_INDEX" == "1" ]]; then
  log "Reconstruindo indice N/G/C da Argiloteca"
  if [[ ! -f "$NGC_SCRIPT" ]]; then
    fail_or_warn "Script N/G/C nao encontrado: $NGC_SCRIPT"
  elif [[ ! -d "$RAW_DIR" ]]; then
    fail_or_warn "RAW_DIR nao encontrado: $RAW_DIR"
  else
    mkdir -p "$NGC_INDEX_DIR"
    "$PYTHON_BIN" "$NGC_SCRIPT" \
      --input-dir "$RAW_DIR" \
      --output-dir "$NGC_INDEX_DIR" \
      --group-by-basename \
      --no-plots 2>&1 | tee -a "$RUN_LOG"
    append_report "- Índice N/G/C reconstruído a partir de \`$RAW_DIR\`."
  fi
else
  warn "Reconstrucao do indice N/G/C pulada por REBUILD_NGC_INDEX=0"
fi

if [[ "$BUILD_DATASET" == "1" ]]; then
  log "Gerando dataset N/G/C para Diffract"
  if [[ ! -f "$DATASET_BUILDER" ]]; then
    fail_or_warn "Builder do dataset nao encontrado: $DATASET_BUILDER"
  elif [[ ! -f "$NGC_INDEX" ]]; then
    fail_or_warn "Indice N/G/C nao encontrado: $NGC_INDEX"
  else
    "$PYTHON_BIN" "$DATASET_BUILDER" \
      --source-index "$NGC_INDEX" \
      --output-dir "$DATASET_DIR" 2>&1 | tee -a "$RUN_LOG"
    append_report "- Dataset N/G/C gerado em \`$DATASET_DIR\`."
    append_report "  - \`ngc_training_samples.jsonl\`"
    append_report "  - \`ngc_training_labels.csv\`"
    append_report "  - \`manifest.json\`"
  fi
else
  warn "Geracao do dataset pulada por BUILD_DATASET=0"
fi

if [[ "$RUN_TRAINING" == "1" ]]; then
  log "Treino solicitado"
  if [[ -f "$NGC_TRAIN_ADAPTER" ]]; then
    if [[ ! -f "$DATASET_DIR/ngc_training_samples.jsonl" ]]; then
      fail_or_warn "Dataset N/G/C nao encontrado para treino: $DATASET_DIR/ngc_training_samples.jsonl"
    else
      log "Treinando adaptador multi-label N/G/C auxiliar"
      "$PYTHON_BIN" "$NGC_TRAIN_ADAPTER" \
        --dataset-jsonl "$DATASET_DIR/ngc_training_samples.jsonl" \
        --model-dir "$NGC_MODEL_DIR" 2>&1 | tee -a "$RUN_LOG"
      append_report "- Adaptador N/G/C treinado em \`$NGC_MODEL_DIR\`."
      append_report "  - \`model.pkl\`"
      append_report "  - \`metrics.json\`"
      append_report "  - \`training_predictions.json\`"
      append_report "  - \`training_report.md\`"
    fi
  elif [[ -f "$TRAIN_SCRIPT" ]]; then
    warn "Script de treino encontrado em $TRAIN_SCRIPT, mas sem adaptador N/G/C de grupo habilitado."
    append_report "- Treino não executado: falta adaptador N/G/C para \`$TRAIN_SCRIPT\`."
    if [[ "$STRICT" == "1" ]]; then
      exit 1
    fi
  else
    fail_or_warn "Nenhum script de treino Diffract encontrado."
  fi
else
  warn "Treino pulado por RUN_TRAINING=0"
fi

if [[ "$RUN_INFERENCE" == "1" ]]; then
  log "Inferencia solicitada"
  if [[ -f "$NGC_MODEL_DIR/training_predictions.json" ]]; then
    mkdir -p "$OUTPUT_DIR"
    cp "$NGC_MODEL_DIR/training_predictions.json" "$OUTPUT_DIR/ngc_group_adapter_predictions.json"
    append_report "- Inferência de auditoria N/G/C exportada para \`$OUTPUT_DIR/ngc_group_adapter_predictions.json\`."
    warn "Inferencia externa ainda nao implementada; exportei as predicoes de auditoria do dataset N/G/C."
  elif [[ -f "$INFER_SCRIPT" ]]; then
    warn "Inferencia XRDNet existente detectada, mas ela espera manifest de curvas Diffract e modelo treinado por curva."
    append_report "- Inferência externa não executada: falta entrada nova N/G/C para amostras fora do dataset."
    if [[ "$STRICT" == "1" ]]; then
      exit 1
    fi
  else
    fail_or_warn "Nenhum script de inferencia Diffract encontrado."
  fi
else
  warn "Inferencia pulada por RUN_INFERENCE=0"
fi

if [[ -f "$DATASET_DIR/ngc_training_samples.jsonl" ]]; then
  SAMPLE_COUNT="$(wc -l < "$DATASET_DIR/ngc_training_samples.jsonl" | tr -d ' ')"
  append_report ""
  append_report "## Dataset"
  append_report ""
  append_report "- Amostras JSONL: $SAMPLE_COUNT"
  append_report "- Política: \`auxiliary_not_confirmatory\`"
  if grep -q '"sample_id": "22-25"' "$DATASET_DIR/ngc_training_samples.jsonl"; then
    append_report "- Validação 22-25: presente no dataset."
  else
    append_report "- Validação 22-25: não encontrado no dataset."
  fi
fi

append_report ""
append_report "## Limitações"
append_report ""
append_report "- O dataset contém rótulos fracos auxiliares por comportamento N/G/C."
append_report "- O adaptador N/G/C treinado neste pipeline é auxiliar e não confirmatório; para produção científica precisa de mais grupos curados e validação externa."
append_report "- DiffractGPT, XRDNet e WebMineral continuam evidências secundárias."
append_report "- O arquivo de regras N/G/C versionado é a fonte das decisões diagnósticas; WebMineral permanece catálogo auxiliar."

log "Relatorio gravado em $REPORT_PATH"
log "Concluido"
