#!/usr/bin/env bash
set -euo pipefail

PANEL_REPO_URL="${PANEL_REPO_URL:-https://github.com/AlexSemeler/argiloteca-drx-panel.git}"
PANEL_REPO_URL_FALLBACK="${PANEL_REPO_URL_FALLBACK:-ssh://git@ssh.github.com:443/AlexSemeler/argiloteca-drx-panel.git}"
PANEL_BRANCH="${PANEL_BRANCH:-codex/atualiza-readme-drx-panel}"
PANEL_REPO_DIR="${PANEL_REPO_DIR:-/home/invenio/invenio-project/argiloteca-drx-panel}"
SOURCE_DIR="${SOURCE_DIR:-}"
APP_ROOT="${APP_ROOT:-}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-}"
BACKUP_ROOT="${BACKUP_ROOT:-/home/invenio/invenio-project/backups}"
RESTART_APP="${RESTART_APP:-1}"
RUN_TESTS="${RUN_TESTS:-0}"
LOCAL_PROBE_URL="${LOCAL_PROBE_URL:-http://127.0.0.1:5000}"
PUBLIC_URL="${PUBLIC_URL:-}"
EXPECTED_ASSET_VERSION="${EXPECTED_ASSET_VERSION:-20260619-rruff-odr-linked-v3}"
DRY_RUN="${DRY_RUN:-0}"

# Aplica no servidor Linux um bundle do painel DRX recebido por rsync ou Git.
# O fluxo sempre detecta runtime, faz backup, copia allow-list e valida marcador.
usage() {
  cat <<'EOF'
Uso no Linux:
  ./linux_baixar_e_atualizar_painel_argiloteca.sh [opcoes]

Opcoes:
  --source-dir DIR    Usa um pacote ja enviado por rsync em vez de baixar do GitHub.
  --branch BRANCH     Branch do repo argiloteca-drx-panel. Padrao: codex/atualiza-readme-drx-panel.
  --app-root DIR      Caminho do app Argiloteca que contem argiloteca_custom/.
  --no-restart        Aplica arquivos, mas nao reinicia a Argiloteca.
  --dry-run           Mostra o que faria, sem copiar nem reiniciar.
  -h, --help          Mostra esta ajuda.

Variaveis uteis:
  PANEL_REPO_URL      URL Git do painel.
  PANEL_REPO_DIR      Onde clonar/atualizar o painel no Linux.
  APP_ROOT            App Argiloteca remoto; detectado automaticamente quando possivel.
  RESTART_APP         1 para reiniciar quando possivel, 0 para nao reiniciar.
  LOCAL_PROBE_URL     URL interna para checar o app. Padrao: http://127.0.0.1:5000.
  PUBLIC_URL          URL publica opcional para conferir proxy/cache.
  EXPECTED_ASSET_VERSION  Marcador esperado no HTML do painel.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-dir)
      SOURCE_DIR="$2"
      shift 2
      ;;
    --branch)
      PANEL_BRANCH="$2"
      shift 2
      ;;
    --app-root)
      APP_ROOT="$2"
      shift 2
      ;;
    --no-restart)
      RESTART_APP=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
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

find_app_root() {
  # Detecta a instalacao Argiloteca real sem assumir layout unico de VM.
  if [[ -n "$APP_ROOT" && -f "$APP_ROOT/argiloteca_custom/argiloteca/static/js/drx-comparacao.js" ]]; then
    printf '%s\n' "$APP_ROOT"
    return 0
  fi

  local candidates=(
    "/home/invenio/invenio-project/argiloteca-local/app"
    "/home/invenio/invenio-project/argiloteca-local/argiloteca"
    "/home/invenio/invenio-project/argiloteca-git/argiloteca"
    "/home/invenio/invenio-project/argiloteca"
    "/home/vmx000080/invenio-project/argiloteca-git/argiloteca"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate/argiloteca_custom/argiloteca/static/js/drx-comparacao.js" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  local found
  found="$(find /home/invenio /home/vmx000080 /srv /opt -type f -path '*/argiloteca_custom/argiloteca/static/js/drx-comparacao.js' -print -quit 2>/dev/null || true)"
  if [[ -n "$found" ]]; then
    printf '%s\n' "${found%/argiloteca_custom/argiloteca/static/js/drx-comparacao.js}"
    return 0
  fi

  return 1
}

detect_python() {
  # Usa o Python do runtime quando existir; python3 e apenas fallback.
  local candidates=(
    "/home/invenio/invenio-project/argiloteca-local/venvs/app-py310-l3/bin/python"
    "/home/invenio/invenio-project/argiloteca-git/.venv/bin/python"
    "$APP_ROOT/.venv/bin/python"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  command -v python3
}

prepare_source() {
  # A fonte pode ser staging enviado pelo Mac ou clone/checkout do GitHub.
  if [[ -n "$SOURCE_DIR" ]]; then
    if [[ ! -d "$SOURCE_DIR" ]]; then
      echo "ERRO: SOURCE_DIR nao existe: $SOURCE_DIR" >&2
      exit 1
    fi
    printf '%s\n' "$SOURCE_DIR"
    return 0
  fi

  if [[ ! -d "$PANEL_REPO_DIR/.git" ]]; then
    mkdir -p "$(dirname "$PANEL_REPO_DIR")"
    if ! git clone "$PANEL_REPO_URL" "$PANEL_REPO_DIR"; then
      echo "Clone via PANEL_REPO_URL falhou; tentando fallback SSH 443..."
      git clone "$PANEL_REPO_URL_FALLBACK" "$PANEL_REPO_DIR"
    fi
  fi

  git -C "$PANEL_REPO_DIR" fetch --all --prune
  git -C "$PANEL_REPO_DIR" checkout "$PANEL_BRANCH"
  git -C "$PANEL_REPO_DIR" pull --ff-only
  printf '%s\n' "$PANEL_REPO_DIR"
}

copy_file() {
  # Copia atomica simples por arquivo allow-listado; dry-run nunca altera app.
  local source="$1"
  local target="$2"
  if [[ ! -f "$source" ]]; then
    echo "ERRO: arquivo fonte ausente: $source" >&2
    exit 1
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "dry-run: cp $source -> $target"
  else
    mkdir -p "$(dirname "$target")"
    cp -p "$source" "$target"
    echo "aplicado: $target"
  fi
}

restart_local_argiloteca_if_possible() {
  # Reinicio opcional do runtime local conhecido, com probe HTTP apos subir.
  if [[ "$RESTART_APP" != "1" ]]; then
    echo "Restart pulado por RESTART_APP=0."
    return 0
  fi

  local runtime_root="/home/invenio/invenio-project/argiloteca-local"
  local runtime_app="$runtime_root/app"
  local runtime_venv="$runtime_root/venvs/app-py310-l3"
  local runtime_env="$runtime_root/secrets/l3-local.env"
  local log_dir="$runtime_root/logs"
  local run_log="$log_dir/invenio-run-drx-panel-$(date -u +%Y%m%dT%H%M%SZ).log"

  if [[ ! -x "$runtime_venv/bin/invenio" || ! -f "$runtime_env" || ! -d "$runtime_app" ]]; then
    echo "Restart automatico nao aplicado: runtime local padrao nao encontrado."
    echo "Reinicie manualmente o servico Argiloteca se o painel ja estava aberto."
    return 0
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "dry-run: reiniciaria $runtime_venv/bin/invenio run -h 127.0.0.1 -p 5000"
    return 0
  fi

  mkdir -p "$log_dir"
  cd "$runtime_app"
  "$runtime_venv/bin/python" -m pip install -e ./argiloteca_custom >/tmp/arg_drx_panel_pip_install.log 2>&1 || {
    cat /tmp/arg_drx_panel_pip_install.log >&2
    return 1
  }

  local pid
  pid="$(pgrep -f 'venvs/app-py310-l3/bin/invenio run -h 127.0.0.1 -p 5000' | head -1 || true)"
  if [[ -n "$pid" ]]; then
    echo "Parando PID atual: $pid"
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      if kill -0 "$pid" 2>/dev/null; then
        sleep 1
      else
        break
      fi
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  fi

  nohup bash -lc "set -a; . '$runtime_env'; set +a; cd '$runtime_app'; exec '$runtime_venv/bin/invenio' run -h 127.0.0.1 -p 5000" > "$run_log" 2>&1 &
  echo "Argiloteca reiniciada. Log: $run_log"

  for i in $(seq 1 45); do
    if curl -k --max-time 3 -sS "$LOCAL_PROBE_URL/drx/comparacao" >/tmp/arg_drx_panel_probe.html 2>/tmp/arg_drx_panel_probe.err; then
      echo "Painel respondeu em ${i}s: $LOCAL_PROBE_URL/drx/comparacao"
      return 0
    fi
    sleep 1
  done

  echo "AVISO: painel nao respondeu no tempo esperado."
  tail -n 80 "$run_log" || true
}

show_applied_markers() {
  # Marcadores ajudam a auditar se o runtime recebeu a versao esperada.
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi

  echo "Marcadores aplicados no servidor:"
  grep -nF "$EXPECTED_ASSET_VERSION" "$APP_ROOT/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html" || true
  grep -nF "chlorite14A: [13.58, 14.87]" "$APP_ROOT/argiloteca_custom/argiloteca/static/js/drx-comparacao.js" || true
  grep -nF '"chlorite14A": (13.58, 14.87)' "$APP_ROOT/argiloteca_custom/argiloteca/services/drx.py" || true
}

check_panel_url_marker() {
  local label="$1"
  local base_url="$2"
  local required="$3"

  if [[ -z "$base_url" || "$DRY_RUN" == "1" ]]; then
    return 0
  fi

  local probe_tmp
  probe_tmp="$(mktemp /tmp/arg_drx_panel_url.XXXXXX)"
  if curl -k --max-time 15 -sS "$base_url/drx/comparacao" > "$probe_tmp"; then
    if grep -Fq "$EXPECTED_ASSET_VERSION" "$probe_tmp"; then
      echo "URL $label OK: $base_url/drx/comparacao contem $EXPECTED_ASSET_VERSION"
      rm -f "$probe_tmp"
      return 0
    fi
    echo "AVISO: URL $label respondeu, mas nao mostra $EXPECTED_ASSET_VERSION."
    rm -f "$probe_tmp"
    [[ "$required" == "1" ]] && return 1 || return 0
  fi

  echo "AVISO: URL $label nao respondeu: $base_url/drx/comparacao"
  rm -f "$probe_tmp"
  [[ "$required" == "1" ]] && return 1 || return 0
}

echo "============================================================"
echo "Atualizar painel DRX no Linux"
echo "============================================================"
echo "PANEL_BRANCH=$PANEL_BRANCH"
echo "PANEL_REPO_URL=$PANEL_REPO_URL"
echo "SOURCE_DIR=${SOURCE_DIR:-<baixar do GitHub>}"
echo "LOCAL_PROBE_URL=$LOCAL_PROBE_URL"
echo "PUBLIC_URL=${PUBLIC_URL:-<nao informado>}"
echo "EXPECTED_ASSET_VERSION=$EXPECTED_ASSET_VERSION"
echo "DRY_RUN=$DRY_RUN"
echo

APP_ROOT="$(find_app_root)" || {
  echo "ERRO: nao encontrei APP_ROOT com argiloteca_custom/." >&2
  echo "Use --app-root /caminho/do/app/argiloteca." >&2
  exit 1
}
if [[ -z "$WORKSPACE_ROOT" ]]; then
  WORKSPACE_ROOT="$(dirname "$APP_ROOT")"
fi
PYTHON_BIN="$(detect_python)"
SOURCE_DIR="$(prepare_source)"

echo "APP_ROOT=$APP_ROOT"
echo "WORKSPACE_ROOT=$WORKSPACE_ROOT"
echo "SOURCE_DIR=$SOURCE_DIR"
echo "PYTHON_BIN=$PYTHON_BIN"
echo

required_sources=(
# Este conjunto precisa existir antes de copiar; evita aplicar deploy parcial.
  "argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js"
  "argiloteca/argiloteca_custom/argiloteca/static/css/drx-comparacao.css"
  "argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html"
  "argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/pacote_analitico.html"
  "argiloteca/argiloteca_custom/argiloteca/views.py"
  "argiloteca/argiloteca_custom/argiloteca/services/drx.py"
  "povoamento/drx/baixar_webmineral_argilominerais.py"
  "povoamento/drx/classificar_minerais_raw.py"
  "povoamento/drx/publicar_resultado_painel_argiloteca.sh"
  "povoamento/drx/reclassificar_minerais_raw.sh"
  "povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_argilominerais_vocabulario.json"
  "povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_xray_referencia.json"
  "povoamento/visualizacao-drx/webmineral/webmineral_argilominerais_vocabulario_manifest.json"
)
for rel in "${required_sources[@]}"; do
  [[ -f "$SOURCE_DIR/$rel" ]] || { echo "ERRO: fonte ausente: $SOURCE_DIR/$rel" >&2; exit 1; }
done

echo "[1] Backup dos arquivos atuais..."
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$BACKUP_ROOT/drx_panel_before_$STAMP"
if [[ "$DRY_RUN" == "1" ]]; then
  echo "dry-run: criaria backup em $BACKUP_DIR"
else
  mkdir -p "$BACKUP_DIR"
  tar --ignore-failed-read -czf "$BACKUP_DIR/argiloteca_drx_panel_runtime.tgz" -C "$APP_ROOT" \
    argiloteca_custom/argiloteca/mineralogia.py \
    argiloteca_custom/argiloteca/services/analytical_packages.py \
    argiloteca_custom/argiloteca/services/drx.py \
    argiloteca_custom/argiloteca/services/geoquimica.py \
    argiloteca_custom/argiloteca/services/raw_snapshot_links.py \
    argiloteca_custom/argiloteca/static/css/drx-comparacao.css \
    argiloteca_custom/argiloteca/static/css/pacote-analitico.css \
    argiloteca_custom/argiloteca/static/js/drx-comparacao.js \
    argiloteca_custom/argiloteca/static/js/pacote-analitico.js \
    argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/analises_index.html \
    argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/argilomineral_detail.html \
    argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/catalogo_autorizado_argilominerais.html \
    argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html \
    argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/pacote_analitico.html \
    argiloteca_custom/argiloteca/views.py
  echo "Backup: $BACKUP_DIR/argiloteca_drx_panel_runtime.tgz"
fi

echo
echo "[2] Aplicando arquivos do painel no app Argiloteca..."
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/mineralogia.py" "$APP_ROOT/argiloteca_custom/argiloteca/mineralogia.py"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/services/analytical_packages.py" "$APP_ROOT/argiloteca_custom/argiloteca/services/analytical_packages.py"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/services/drx.py" "$APP_ROOT/argiloteca_custom/argiloteca/services/drx.py"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/services/geoquimica.py" "$APP_ROOT/argiloteca_custom/argiloteca/services/geoquimica.py"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/services/raw_snapshot_links.py" "$APP_ROOT/argiloteca_custom/argiloteca/services/raw_snapshot_links.py"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/static/css/drx-comparacao.css" "$APP_ROOT/argiloteca_custom/argiloteca/static/css/drx-comparacao.css"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/static/css/pacote-analitico.css" "$APP_ROOT/argiloteca_custom/argiloteca/static/css/pacote-analitico.css"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js" "$APP_ROOT/argiloteca_custom/argiloteca/static/js/drx-comparacao.js"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/static/js/pacote-analitico.js" "$APP_ROOT/argiloteca_custom/argiloteca/static/js/pacote-analitico.js"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/analises_index.html" "$APP_ROOT/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/analises_index.html"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/argilomineral_detail.html" "$APP_ROOT/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/argilomineral_detail.html"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/catalogo_autorizado_argilominerais.html" "$APP_ROOT/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/catalogo_autorizado_argilominerais.html"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html" "$APP_ROOT/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/pacote_analitico.html" "$APP_ROOT/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/pacote_analitico.html"
copy_file "$SOURCE_DIR/argiloteca/argiloteca_custom/argiloteca/views.py" "$APP_ROOT/argiloteca_custom/argiloteca/views.py"

if [[ -f "$SOURCE_DIR/povoamento/drx/gerar_metricas_painel_drx.py" ]]; then
  copy_file "$SOURCE_DIR/povoamento/drx/gerar_metricas_painel_drx.py" "$WORKSPACE_ROOT/povoamento/drx/gerar_metricas_painel_drx.py"
fi
copy_file "$SOURCE_DIR/povoamento/drx/baixar_webmineral_argilominerais.py" "$WORKSPACE_ROOT/povoamento/drx/baixar_webmineral_argilominerais.py"
copy_file "$SOURCE_DIR/povoamento/drx/classificar_minerais_raw.py" "$WORKSPACE_ROOT/povoamento/drx/classificar_minerais_raw.py"
copy_file "$SOURCE_DIR/povoamento/drx/publicar_resultado_painel_argiloteca.sh" "$WORKSPACE_ROOT/povoamento/drx/publicar_resultado_painel_argiloteca.sh"
copy_file "$SOURCE_DIR/povoamento/drx/reclassificar_minerais_raw.sh" "$WORKSPACE_ROOT/povoamento/drx/reclassificar_minerais_raw.sh"
copy_file "$SOURCE_DIR/povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_argilominerais_vocabulario.json" "$WORKSPACE_ROOT/povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_argilominerais_vocabulario.json"
copy_file "$SOURCE_DIR/povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_xray_referencia.json" "$WORKSPACE_ROOT/povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_xray_referencia.json"
copy_file "$SOURCE_DIR/povoamento/visualizacao-drx/webmineral/webmineral_argilominerais_vocabulario_manifest.json" "$WORKSPACE_ROOT/povoamento/visualizacao-drx/webmineral/webmineral_argilominerais_vocabulario_manifest.json"

echo
echo "[3] Validando arquivos aplicados..."
if [[ "$DRY_RUN" == "1" ]]; then
  echo "dry-run: validacao pulada."
else
  "$PYTHON_BIN" -m py_compile \
    "$APP_ROOT/argiloteca_custom/argiloteca/mineralogia.py" \
    "$APP_ROOT/argiloteca_custom/argiloteca/services/analytical_packages.py" \
    "$APP_ROOT/argiloteca_custom/argiloteca/services/drx.py" \
    "$APP_ROOT/argiloteca_custom/argiloteca/services/geoquimica.py" \
    "$APP_ROOT/argiloteca_custom/argiloteca/services/raw_snapshot_links.py" \
    "$APP_ROOT/argiloteca_custom/argiloteca/views.py" \
    "$WORKSPACE_ROOT/povoamento/drx/gerar_metricas_painel_drx.py" \
    "$WORKSPACE_ROOT/povoamento/drx/baixar_webmineral_argilominerais.py" \
    "$WORKSPACE_ROOT/povoamento/drx/classificar_minerais_raw.py"
  if command -v node >/dev/null 2>&1; then
    node --check "$APP_ROOT/argiloteca_custom/argiloteca/static/js/drx-comparacao.js"
    node --check "$APP_ROOT/argiloteca_custom/argiloteca/static/js/pacote-analitico.js"
  else
    echo "node nao encontrado; validacao JS pulada no Linux."
  fi
fi

echo
echo "[4] Conferindo marcadores aplicados..."
show_applied_markers

if [[ "$RUN_TESTS" == "1" && "$DRY_RUN" != "1" ]]; then
  echo
  echo "[5] Rodando testes do painel no Linux..."
  PYTHONPATH="$APP_ROOT:$APP_ROOT/argiloteca_custom" "$PYTHON_BIN" -m unittest discover -s "$SOURCE_DIR/argiloteca/argiloteca_custom/tests"
fi

echo
echo "[6] Reinicio/checagem do painel..."
restart_local_argiloteca_if_possible
check_panel_url_marker "interna" "$LOCAL_PROBE_URL" 1
check_panel_url_marker "publica" "$PUBLIC_URL" 0

echo
echo "Atualizacao do painel DRX concluida."
