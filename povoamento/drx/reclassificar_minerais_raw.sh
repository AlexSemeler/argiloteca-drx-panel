#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/argilas/argilas"
# Caminhos da instalacao local: os RAWs sao somente entrada; as saidas abaixo
# sao snapshots derivados consumidos pelo painel.
OUT_DIR="$REPO_ROOT/povoamento/visualizacao-drx/saida_argiloteca_drx"
RAW_DIR="$REPO_ROOT/povoamento/visualizacao-drx/raw"
VOCAB="$OUT_DIR/webmineral_argilominerais_vocabulario.json"
PYCACHE="/private/tmp/arg_drx_reclass_pycache"
TOP_CANDIDATES="${TOP_CANDIDATES:-8}"

cd "$REPO_ROOT"

if [[ ! -d "$RAW_DIR" ]]; then
  echo "ERRO: pasta RAW nao encontrada: $RAW_DIR" >&2
  exit 1
fi

# O vocabulario WebMineral local traz as faixas diagnosticas usadas para
# comparar picos/d-spacing sem depender de rede durante a reclassificacao.
if [[ ! -f "$VOCAB" ]]; then
  echo "ERRO: vocabulario WebMineral nao encontrado: $VOCAB" >&2
  exit 1
fi

RAW_COUNT="$(find "$RAW_DIR" -type f -iname "*.raw" | wc -l | tr -d " ")"

echo "Limpando apenas saidas derivadas antigas de classificacao mineralogica..."
rm -f \
  "$OUT_DIR/classificacao_mineralogica_raw.json" \
  "$OUT_DIR/classificacao_mineralogica_resumo.json" \
  "$OUT_DIR/classificacao_mineralogica_raw.csv"

echo "Classificacao que sera aplicada aos RAWs:"
echo "  RAWs encontrados: $RAW_COUNT"
echo "  Pasta RAW: $RAW_DIR"
echo "  Vocabulario: $VOCAB"
echo "  Candidatos por amostra: $TOP_CANDIDATES"
# Mostra as faixas N/G/C, clorita e quartzo antes de processar para deixar
# explicito o criterio cientifico que sera aplicado pelo classificador.
PYTHONPATH="$REPO_ROOT:$REPO_ROOT/argiloteca/argiloteca_custom" \
PYTHONPYCACHEPREFIX="$PYCACHE" \
/usr/bin/python3 - <<'PY'
from argiloteca.services.drx import DRX_DIAGNOSTIC_D_RANGES

labels = [
    ("Ilita 10A", "illite10A"),
    ("Caulinita 7A", "kaolinite7A"),
    ("Esmectita natural", "smectiteNatural"),
    ("Esmectita glicolada", "smectiteGlycolated"),
    ("Esmectita calcinada", "smectiteCalcined"),
    ("Clorita 001 basal", "chlorite14A"),
    ("Quartzo 101", "quartz101"),
    ("Quartzo 100", "quartz100"),
]

for label, key in labels:
    d_min, d_max = DRX_DIAGNOSTIC_D_RANGES[key]
    print(f"  {label}: {d_min:g}-{d_max:g} A")
PY

echo "Aplicando classificacao mineralogica aos RAWs agora..."
# A chamada abaixo so le os RAWs e escreve JSON/CSV derivados no OUT_DIR.
# TOP_CANDIDATES controla quantas semelhancas WebMineral sao mantidas por amostra.
PYTHONPATH="$REPO_ROOT:$REPO_ROOT/argiloteca/argiloteca_custom" \
PYTHONPYCACHEPREFIX="$PYCACHE" \
/usr/bin/python3 povoamento/drx/classificar_minerais_raw.py \
  --input "$RAW_DIR" \
  --output-dir "$OUT_DIR" \
  --cache-referencia "$VOCAB" \
  --top-candidates "$TOP_CANDIDATES"

echo "Concluido."
echo "Saidas geradas:"
echo "  $OUT_DIR/classificacao_mineralogica_raw.json"
echo "  $OUT_DIR/classificacao_mineralogica_resumo.json"
echo "  $OUT_DIR/classificacao_mineralogica_raw.csv"
