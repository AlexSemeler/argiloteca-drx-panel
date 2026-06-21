#!/usr/bin/env bash
set -euo pipefail

PANEL_REPO_DIR="/Users/argilas/argilas/repos/argiloteca-drx-panel"
REMOTE="${REMOTE:-invenio@192.168.0.16}"
REMOTE_STAGE="${REMOTE_STAGE:-/home/invenio/invenio-project/argiloteca-drx-panel-upload}"
REMOTE_SCRIPT="${REMOTE_SCRIPT:-/home/invenio/invenio-project/linux_baixar_e_atualizar_painel_argiloteca.sh}"
PANEL_BRANCH="${PANEL_BRANCH:-codex/atualiza-readme-drx-panel}"
RESTART_APP="${RESTART_APP:-1}"
RUN_REMOTE_APPLY="${RUN_REMOTE_APPLY:-1}"
LOCAL_PROBE_URL="${LOCAL_PROBE_URL:-http://127.0.0.1:5000}"
PUBLIC_URL="${PUBLIC_URL:-https://192.168.0.16}"
EXPECTED_ASSET_VERSION="${EXPECTED_ASSET_VERSION:-20260619-rruff-odr-linked-v3}"
VERIFY_PUBLIC="${VERIFY_PUBLIC:-1}"
DRY_RUN="${DRY_RUN:-0}"
SSH_CONTROL_PATH="${SSH_CONTROL_PATH:-/tmp/arg_drx_panel_192_168_0_16_%r_%h_%p}"
SSH_OPTS=(
  -o ControlMaster=auto
  -o ControlPersist=20m
  -o ControlPath="$SSH_CONTROL_PATH"
)
RSYNC_RSH="ssh -o ControlMaster=auto -o ControlPersist=20m -o ControlPath=$SSH_CONTROL_PATH"

# Envia o bundle allow-listado para staging remoto e, opcionalmente, aciona o
# script Linux de aplicacao. O dry-run e intencional para auditar antes do deploy.
usage() {
  cat <<'EOF'
Uso no Mac:
  ./enviar_painel_para_linux_192_168_0_16.sh [opcoes]

Opcoes:
  --remote USER@HOST      Padrao: invenio@192.168.0.16.
  --stage DIR             Pasta remota de staging.
  --remote-script PATH    Caminho do script Linux remoto.
  --no-apply              Envia os arquivos, mas nao aplica no app remoto.
  --no-restart            Aplica no app remoto sem reiniciar Argiloteca.
  --public-url URL        URL publica para conferir a versao publicada.
  --no-public-check       Nao checa a URL publica depois de aplicar.
  --dry-run               Mostra o rsync e comando remoto sem alterar o servidor.
  -h, --help              Mostra esta ajuda.

Variaveis uteis:
  REMOTE                  Usuario e host SSH.
  REMOTE_STAGE            Staging remoto.
  REMOTE_SCRIPT           Caminho remoto do script de atualizacao.
  RUN_REMOTE_APPLY        1 para aplicar apos enviar, 0 para apenas enviar.
  RESTART_APP             1 para reiniciar quando possivel, 0 para nao reiniciar.
  PUBLIC_URL              URL publica esperada. Padrao: https://192.168.0.16.
  EXPECTED_ASSET_VERSION  Marcador esperado no HTML do painel.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      REMOTE="$2"
      shift 2
      ;;
    --stage)
      REMOTE_STAGE="$2"
      shift 2
      ;;
    --remote-script)
      REMOTE_SCRIPT="$2"
      shift 2
      ;;
    --no-apply)
      RUN_REMOTE_APPLY=0
      shift
      ;;
    --no-restart)
      RESTART_APP=0
      shift
      ;;
    --public-url)
      PUBLIC_URL="$2"
      shift 2
      ;;
    --no-public-check)
      VERIFY_PUBLIC=0
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

if [[ ! -d "$PANEL_REPO_DIR/.git" ]]; then
  echo "ERRO: repo local do painel nao encontrado: $PANEL_REPO_DIR" >&2
  exit 1
fi

cd "$PANEL_REPO_DIR"

# Homebrew rsync preserva melhor o comportamento esperado no macOS deste fluxo.
if command -v /opt/homebrew/bin/rsync >/dev/null 2>&1; then
  RSYNC_BIN="/opt/homebrew/bin/rsync"
else
  RSYNC_BIN="rsync"
fi

TMP_LIST="$(mktemp /private/tmp/arg_drx_panel_files.XXXXXX)"
trap 'rm -f "$TMP_LIST"' EXIT

# Arquivos permitidos no deploy remoto. Dados RAW e saidas pesadas ficam fora do
# pacote para reduzir risco e manter o servidor reproduzivel.
cat > "$TMP_LIST" <<'EOF_LIST'
.gitignore
EXPLICACAO_PAINEL_DRX_COMPARACAO.md
README.md
REPOSITORY_SCOPE.md
enviar_atualizacoes_argiloteca_drx_panel.sh
enviar_painel_para_linux_192_168_0_16.sh
linux_baixar_e_atualizar_painel_argiloteca.sh
argiloteca/argiloteca_custom/argiloteca/mineralogia.py
argiloteca/argiloteca_custom/argiloteca/services/analytical_packages.py
argiloteca/argiloteca_custom/argiloteca/services/drx.py
argiloteca/argiloteca_custom/argiloteca/services/geoquimica.py
argiloteca/argiloteca_custom/argiloteca/services/raw_snapshot_links.py
argiloteca/argiloteca_custom/argiloteca/static/css/drx-comparacao.css
argiloteca/argiloteca_custom/argiloteca/static/css/pacote-analitico.css
argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js
argiloteca/argiloteca_custom/argiloteca/static/js/pacote-analitico.js
argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/analises_index.html
argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/argilomineral_detail.html
argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/catalogo_autorizado_argilominerais.html
argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html
argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/pacote_analitico.html
argiloteca/argiloteca_custom/argiloteca/views.py
argiloteca/argiloteca_custom/tests/test_drx.py
argiloteca/argiloteca_custom/tests/test_raw_snapshot_links.py
povoamento/drx/gerar_metricas_painel_drx.py
povoamento/drx/baixar_webmineral_argilominerais.py
povoamento/drx/classificar_minerais_raw.py
povoamento/drx/publicar_resultado_painel_argiloteca.sh
povoamento/drx/reclassificar_minerais_raw.sh
povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_argilominerais_vocabulario.json
povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_xray_referencia.json
povoamento/visualizacao-drx/webmineral/webmineral_argilominerais_vocabulario_manifest.json
EOF_LIST

echo "============================================================"
echo "Enviar painel DRX para Linux"
echo "============================================================"
echo "Repo local: $PANEL_REPO_DIR"
echo "Remote: $REMOTE"
echo "Stage remoto: $REMOTE_STAGE"
echo "Script remoto: $REMOTE_SCRIPT"
echo "Aplicar remoto: $RUN_REMOTE_APPLY"
echo "Reiniciar app: $RESTART_APP"
echo "URL publica: $PUBLIC_URL"
echo "Versao esperada: $EXPECTED_ASSET_VERSION"
echo "Checar URL publica: $VERIFY_PUBLIC"
echo "Dry-run: $DRY_RUN"
echo

echo "[1] Validando repo local..."
# Validacoes locais falham cedo antes de qualquer SSH/rsync real.
git diff --check
if command -v node >/dev/null 2>&1; then
  node --check argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js
  node --check argiloteca/argiloteca_custom/argiloteca/static/js/pacote-analitico.js
else
  echo "AVISO: node nao encontrado; validacao JS local pulada."
fi
if [[ -x /Users/argilas/venvs/argiloteca-rdm12/bin/python ]]; then
  PYTHON_BIN="/Users/argilas/venvs/argiloteca-rdm12/bin/python"
else
  PYTHON_BIN="python3"
fi
"$PYTHON_BIN" -m py_compile \
  argiloteca/argiloteca_custom/argiloteca/mineralogia.py \
  argiloteca/argiloteca_custom/argiloteca/services/analytical_packages.py \
  argiloteca/argiloteca_custom/argiloteca/services/drx.py \
  argiloteca/argiloteca_custom/argiloteca/services/geoquimica.py \
  argiloteca/argiloteca_custom/argiloteca/services/raw_snapshot_links.py \
  argiloteca/argiloteca_custom/argiloteca/views.py \
  povoamento/drx/gerar_metricas_painel_drx.py \
  povoamento/drx/baixar_webmineral_argilominerais.py \
  povoamento/drx/classificar_minerais_raw.py
echo "Validacao local OK."

echo
echo "[2] Criando staging remoto..."
if [[ "$DRY_RUN" == "1" ]]; then
  echo "dry-run: ssh $REMOTE mkdir -p $(dirname "$REMOTE_SCRIPT") $REMOTE_STAGE"
else
  ssh "${SSH_OPTS[@]}" "$REMOTE" "mkdir -p '$(dirname "$REMOTE_SCRIPT")' '$REMOTE_STAGE'"
fi

echo
echo "[3] Enviando arquivos permitidos para staging remoto..."
# A copia vai para staging; a aplicacao no runtime acontece em etapa separada.
if [[ "$DRY_RUN" == "1" ]]; then
  "$RSYNC_BIN" -avzn --files-from="$TMP_LIST" -e "$RSYNC_RSH" "$PANEL_REPO_DIR/" "$REMOTE:$REMOTE_STAGE/"
  echo "dry-run: enviaria linux_baixar_e_atualizar_painel_argiloteca.sh para $REMOTE_SCRIPT"
else
  "$RSYNC_BIN" -av --files-from="$TMP_LIST" -e "$RSYNC_RSH" "$PANEL_REPO_DIR/" "$REMOTE:$REMOTE_STAGE/"
  "$RSYNC_BIN" -av -e "$RSYNC_RSH" \
    "$PANEL_REPO_DIR/linux_baixar_e_atualizar_painel_argiloteca.sh" \
    "$REMOTE:$REMOTE_SCRIPT"
  ssh "${SSH_OPTS[@]}" "$REMOTE" "chmod +x '$REMOTE_SCRIPT'"
fi

if [[ "$RUN_REMOTE_APPLY" != "1" ]]; then
  echo
  echo "Arquivos enviados. Para aplicar no servidor:"
  echo "  ssh $REMOTE"
  echo "  SOURCE_DIR='$REMOTE_STAGE' RESTART_APP='$RESTART_APP' LOCAL_PROBE_URL='$LOCAL_PROBE_URL' PUBLIC_URL='$PUBLIC_URL' EXPECTED_ASSET_VERSION='$EXPECTED_ASSET_VERSION' '$REMOTE_SCRIPT' --source-dir '$REMOTE_STAGE'"
  exit 0
fi

echo
echo "[4] Aplicando update no app remoto..."
if [[ "$DRY_RUN" == "1" ]]; then
  echo "dry-run: SOURCE_DIR='$REMOTE_STAGE' RESTART_APP='$RESTART_APP' LOCAL_PROBE_URL='$LOCAL_PROBE_URL' PUBLIC_URL='$PUBLIC_URL' EXPECTED_ASSET_VERSION='$EXPECTED_ASSET_VERSION' '$REMOTE_SCRIPT' --source-dir '$REMOTE_STAGE' --dry-run"
else
  ssh "${SSH_OPTS[@]}" "$REMOTE" \
    "SOURCE_DIR='$REMOTE_STAGE' PANEL_BRANCH='$PANEL_BRANCH' RESTART_APP='$RESTART_APP' LOCAL_PROBE_URL='$LOCAL_PROBE_URL' PUBLIC_URL='$PUBLIC_URL' EXPECTED_ASSET_VERSION='$EXPECTED_ASSET_VERSION' '$REMOTE_SCRIPT' --source-dir '$REMOTE_STAGE'"
fi

check_public_from_mac() {
  # Conferencia externa simples para detectar proxy/cache servindo asset antigo.
  if [[ "$VERIFY_PUBLIC" != "1" || -z "$PUBLIC_URL" || "$DRY_RUN" == "1" ]]; then
    return 0
  fi

  local probe_tmp
  probe_tmp="$(mktemp /private/tmp/arg_drx_panel_public.XXXXXX)"
  if curl -k --max-time 15 -sS "$PUBLIC_URL/drx/comparacao" > "$probe_tmp"; then
    if grep -Fq "$EXPECTED_ASSET_VERSION" "$probe_tmp"; then
      echo "URL publica OK: $PUBLIC_URL/drx/comparacao contem $EXPECTED_ASSET_VERSION"
      rm -f "$probe_tmp"
      return 0
    fi
    echo "ERRO: a URL publica respondeu, mas ainda nao mostra a versao $EXPECTED_ASSET_VERSION." >&2
    echo "Confira se o navegador esta abrindo esta URL ou se o proxy aponta para outro runtime:" >&2
    echo "  $PUBLIC_URL/drx/comparacao" >&2
    rm -f "$probe_tmp"
    return 1
  fi

  echo "AVISO: nao consegui checar a URL publica pelo Mac: $PUBLIC_URL/drx/comparacao"
  rm -f "$probe_tmp"
  return 0
}

echo
echo "[5] Checando URL publica..."
check_public_from_mac

echo
echo "Concluido."
