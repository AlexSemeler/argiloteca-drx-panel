#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/argilas/argilas"
# O painel le diretamente estes artefatos derivados; o script valida contratos
# e gera manifestos, sem tocar nos RAWs originais.
OUT_DIR="$REPO_ROOT/povoamento/visualizacao-drx/saida_argiloteca_drx"
CLASSIFICATION_JSON="$OUT_DIR/classificacao_mineralogica_raw.json"
SUMMARY_JSON="$OUT_DIR/classificacao_mineralogica_resumo.json"
CLASSIFICATION_CSV="$OUT_DIR/classificacao_mineralogica_raw.csv"
TREATMENT_JSON="$OUT_DIR/classificacao_tratamento_raw.json"
VOCAB="$OUT_DIR/webmineral_argilominerais_vocabulario.json"
PUBLISH_MANIFEST="$OUT_DIR/publicacao_painel_drx.json"
METRICS_OUT="$REPO_ROOT/reports/drx_panel_metrics.json"
RESTART_SCRIPT="$REPO_ROOT/argiloteca/arquivos-sh/scripts-funcionais/v64_restart_local_https.sh"
BASE_URL="${BASE_URL:-https://127.0.0.1:5443}"
PYCACHE="${PYCACHE:-/private/tmp/arg_drx_publish_panel_pycache}"
RESTART_LOCAL="${RESTART_LOCAL:-1}"
CHECK_API="${CHECK_API:-1}"

usage() {
  cat <<'EOF'
Uso:
  povoamento/drx/publicar_resultado_painel_argiloteca.sh [opcoes]

Opcoes:
  --restart-local     Reinicia o HTTPS local apos validar os dados. Padrao.
  --no-restart        Nao reinicia o servidor; apenas valida e gera manifestos.
  --check-api         Consulta a API local apos publicar. Padrao.
  --no-api-check      Nao consulta a API local.
  -h, --help          Mostra esta ajuda.

Variaveis opcionais:
  BASE_URL            Padrao: https://127.0.0.1:5443
  RESTART_LOCAL       1 ou 0
  CHECK_API           1 ou 0
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --restart-local)
      RESTART_LOCAL=1
      shift
      ;;
    --no-restart)
      RESTART_LOCAL=0
      shift
      ;;
    --check-api)
      CHECK_API=1
      shift
      ;;
    --no-api-check)
      CHECK_API=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERRO: opcao desconhecida: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_file() {
  local path="$1"
  local label="$2"
# Falha cedo para impedir publicacao parcial quando algum artefato derivado
# essencial do pipeline DRX nao foi produzido.
  if [[ ! -f "$path" ]]; then
    echo "ERRO: $label nao encontrado: $path" >&2
    exit 1
  fi
}

cd "$REPO_ROOT"

echo "Publicando resultado DRX no painel da Argiloteca..."
echo "  Snapshot mineralogico: $CLASSIFICATION_JSON"
echo "  Resumo: $SUMMARY_JSON"
echo "  Vocabulario: $VOCAB"
echo "  Painel: $BASE_URL/drx/comparacao"
echo

require_file "$CLASSIFICATION_JSON" "snapshot de classificacao mineralogica"
require_file "$SUMMARY_JSON" "resumo da classificacao mineralogica"
require_file "$CLASSIFICATION_CSV" "CSV da classificacao mineralogica"
require_file "$VOCAB" "vocabulario WebMineral local"

echo "[1] Validando snapshot que o painel ira ler..."
# A validacao embutida confere a forma do JSON, as faixas diagnosticas e gera
# um manifesto rastreavel com hashes dos artefatos publicados.
PYTHONPYCACHEPREFIX="$PYCACHE" /usr/bin/python3 - "$CLASSIFICATION_JSON" "$SUMMARY_JSON" "$VOCAB" "$PUBLISH_MANIFEST" "$METRICS_OUT" "$BASE_URL" <<'PY'
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

classification_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
vocab_path = Path(sys.argv[3])
manifest_path = Path(sys.argv[4])
metrics_path = Path(sys.argv[5])
base_url = sys.argv[6].rstrip("/")


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


payload = load_json(classification_path)
summary = load_json(summary_path)
vocab = load_json(vocab_path)

if not isinstance(payload, dict):
    raise SystemExit("Snapshot mineralogico invalido: raiz nao e objeto JSON.")
rows = payload.get("results")
if not isinstance(rows, list):
    raise SystemExit("Snapshot mineralogico invalido: chave 'results' ausente.")
if not rows:
    raise SystemExit("Snapshot mineralogico sem resultados; nao vou publicar vazio.")

status = Counter(str(row.get("status") or "sem_status") for row in rows if isinstance(row, dict))
with_candidates = sum(1 for row in rows if isinstance(row, dict) and (row.get("candidates") or row.get("mineral_candidates")))
with_peaks = sum(1 for row in rows if isinstance(row, dict) and (row.get("peaks") or row.get("detected_peaks")))
diagnostic_ranges = vocab.get("diagnostic_ranges") if isinstance(vocab, dict) else {}

# Mantem o contrato cientifico minimo do painel: N/G/C, clorita e quartzo devem
# conservar as janelas de d-spacing esperadas antes de qualquer restart/API check.
required_ranges = {
    "illite_10a": (9.73, 10.38),
    "illite_10a_natural": (9.84, 10.36),
    "illite_10a_glycolated": (9.82, 10.30),
    "illite_10a_calcined": (9.73, 10.38),
    "kaolinite_7a": (6.96, 7.42),
    "kaolinite_7a_natural": (6.97, 7.42),
    "kaolinite_7a_glycolated": (6.96, 7.42),
    "kaolinite_7a_calcined_check": (6.96, 7.42),
    "smectite_natural": (13.46, 16.86),
    "smectite_glycolated": (16.06, 18.31),
    "smectite_calcined": (9.65, 10.37),
    "chlorite_001_basal": (13.58, 14.87),
    "chlorite_001_natural": (13.74, 14.74),
    "chlorite_001_glycolated": (13.83, 14.72),
    "chlorite_001_calcined": (13.58, 14.87),
    "quartz_101": (3.27, 3.42),
    "quartz_101_natural": (3.28, 3.41),
    "quartz_101_glycolated": (3.28, 3.42),
    "quartz_101_calcined": (3.27, 3.42),
    "quartz_100": (4.23, 4.35),
}
range_errors = []
for key, expected in required_ranges.items():
    row = diagnostic_ranges.get(key) if isinstance(diagnostic_ranges, dict) else None
    got = None
    if isinstance(row, dict):
        got = (float(row.get("d_min")), float(row.get("d_max")))
    if got != expected:
        range_errors.append(f"{key}: esperado {expected}, encontrado {got}")
if range_errors:
    raise SystemExit("Faixas diagnosticas do vocabulario nao conferem: " + "; ".join(range_errors))

manifest = {
    "published_at": datetime.now(timezone.utc).isoformat(),
    "panel_url": f"{base_url}/drx/comparacao",
    "api_snapshot_url": f"{base_url}/api/argiloteca/drx/raw-snapshot?limit=20",
    "classification_json": str(classification_path),
    "classification_sha256": sha256_file(classification_path),
    "summary_json": str(summary_path),
    "summary_sha256": sha256_file(summary_path),
    "vocabulary_json": str(vocab_path),
    "vocabulary_sha256": sha256_file(vocab_path),
    "metrics_json": str(metrics_path),
    "total_results": len(rows),
    "status": dict(status),
    "with_candidates": with_candidates,
    "with_detected_peaks": with_peaks,
    "diagnostic_ranges": diagnostic_ranges,
    "summary": summary if isinstance(summary, dict) else {},
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

print(f"  Resultados: {len(rows)}")
print(f"  Status: {dict(status)}")
print(f"  Com candidatos: {with_candidates}")
print(f"  Com picos detectados: {with_peaks}")
print(f"  Manifesto de publicacao: {manifest_path}")
print(f"  SHA256 snapshot: {manifest['classification_sha256']}")
PY

echo
echo "[2] Gerando metricas do painel..."
# As metricas agregadas ajudam a auditar cobertura de candidatos/picos sem
# reprocessar os difratogramas no frontend.
PYTHONPATH="$REPO_ROOT:$REPO_ROOT/argiloteca/argiloteca_custom" \
PYTHONPYCACHEPREFIX="$PYCACHE" \
/usr/bin/python3 povoamento/drx/gerar_metricas_painel_drx.py \
  --raw-snapshot "$CLASSIFICATION_JSON" \
  --treatment-snapshot "$TREATMENT_JSON" \
  --output "$METRICS_OUT"

echo
echo "[3] Publicacao local preparada."
echo "  O painel le diretamente: $CLASSIFICATION_JSON"
echo "  Manifesto: $PUBLISH_MANIFEST"
echo "  Metricas: $METRICS_OUT"

if [[ "$RESTART_LOCAL" == "1" ]]; then
  require_file "$RESTART_SCRIPT" "script de restart local"
  echo
  echo "[4] Reiniciando servidor HTTPS local para limpar cache do painel..."
# Restart e API check ficam parametrizados para permitir dry-run operacional em
# maquinas onde o servico local nao deve ser reiniciado automaticamente.
  "$RESTART_SCRIPT"
else
  echo
  echo "[4] Restart pulado."
  echo "  Se o servidor ja estava aberto, reinicie antes de conferir o painel."
fi

if [[ "$CHECK_API" == "1" ]]; then
  echo
  echo "[5] Conferindo API local do painel..."
# A consulta confirma que Invenio/Argiloteca esta servindo o snapshot recem
# validado, mas nao bloqueia quando o servidor local estiver fora do ar.
  if ! command -v curl >/dev/null 2>&1; then
    echo "  curl nao encontrado; pulei a consulta da API."
  else
    TMP_API="/private/tmp/arg_drx_panel_publish_api_check.json"
    if curl -k -sS --max-time 30 "$BASE_URL/api/argiloteca/drx/raw-snapshot?limit=1" -o "$TMP_API"; then
      /usr/bin/python3 - "$TMP_API" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
pagination = payload.get("pagination") or {}
meta = payload.get("meta") or {}
print(f"  API success: {payload.get('success')}")
print(f"  Total filtrado: {pagination.get('total')}")
print(f"  Total no snapshot: {meta.get('raw_files_total')}")
print(f"  Snapshot path: {payload.get('snapshot_path')}")
PY
    else
      echo "  API local indisponivel em $BASE_URL; confira se o servidor abriu."
    fi
  fi
fi

echo
echo "Concluido. Abra: $BASE_URL/drx/comparacao"
