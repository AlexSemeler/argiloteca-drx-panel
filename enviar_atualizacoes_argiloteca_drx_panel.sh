#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/Users/argilas/argilas/repos/argiloteca-drx-panel"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-$(git -C "$REPO_DIR" branch --show-current)}"
MAIN_BRANCH="${MAIN_BRANCH:-main}"
UPDATE_MAIN="${UPDATE_MAIN:-1}"
COMMIT_MSG="${COMMIT_MSG:-Atualiza painel DRX e scripts de publicacao}"
DEFAULT_VENV_PYTHON="/Users/argilas/venvs/argiloteca-rdm12/bin/python"
if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x "$DEFAULT_VENV_PYTHON" ]]; then
    PYTHON_BIN="$DEFAULT_VENV_PYTHON"
  else
    PYTHON_BIN="python3"
  fi
fi
NODE_BIN="${NODE_BIN:-node}"
TRY_SSH_443="${TRY_SSH_443:-1}"
SSH_443_URL="ssh://git@ssh.github.com:443/AlexSemeler/argiloteca-drx-panel.git"

cd "$REPO_DIR"

# Publica somente o recorte do painel DRX. O script valida antes de stagear e
# bloqueia RAWs, caches e relatorios pesados para evitar vazamento operacional.
echo "============================================================"
echo "Enviar atualizacoes - argiloteca-drx-panel"
echo "============================================================"
echo "Repo: $REPO_DIR"
echo "Remote: $REMOTE"
echo "Branch: $BRANCH"
echo "Atualizar main: $UPDATE_MAIN ($MAIN_BRANCH)"
echo "Mensagem: $COMMIT_MSG"
echo "Python: $PYTHON_BIN"
echo

remote_url="$(git remote get-url "$REMOTE" 2>/dev/null || true)"
if [[ -z "$remote_url" ]]; then
  echo "ERRO: remote '$REMOTE' nao encontrado." >&2
  exit 1
fi

# Guarda contra executar este script em outro repositório por engano.
if [[ "$remote_url" != *"AlexSemeler/argiloteca-drx-panel"* ]]; then
  echo "ERRO: remote inesperado para este script: $remote_url" >&2
  echo "Esperado: AlexSemeler/argiloteca-drx-panel" >&2
  exit 1
fi

echo "[1] Validando diferencas..."
git diff --check

echo
echo "[2] Validando Python..."
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

echo
echo "[3] Validando scripts shell..."
bash -n enviar_atualizacoes_argiloteca_drx_panel.sh
bash -n enviar_painel_para_linux_192_168_0_16.sh
bash -n linux_baixar_e_atualizar_painel_argiloteca.sh
bash -n povoamento/drx/reclassificar_minerais_raw.sh
bash -n povoamento/drx/publicar_resultado_painel_argiloteca.sh

echo
echo "[4] Validando JavaScript..."
if command -v "$NODE_BIN" >/dev/null 2>&1; then
  "$NODE_BIN" --check argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js
  "$NODE_BIN" --check argiloteca/argiloteca_custom/argiloteca/static/js/pacote-analitico.js
else
  echo "AVISO: node nao encontrado; validacao JS pulada."
fi

echo
echo "[5] Rodando testes do recorte DRX..."
PYTHONPATH="$REPO_DIR:$REPO_DIR/argiloteca/argiloteca_custom" \
"$PYTHON_BIN" -m unittest discover -s argiloteca/argiloteca_custom/tests

echo
echo "[6] Preparando arquivos permitidos para commit..."
# Lista allow-listada: codigo, templates, testes e manifestos derivados leves.
# RAWs, var/, reports pesados e caches seguem fora do staging.
git add \
  .gitignore \
  EXPLICACAO_PAINEL_DRX_COMPARACAO.md \
  README.md \
  REPOSITORY_SCOPE.md \
  enviar_atualizacoes_argiloteca_drx_panel.sh \
  enviar_painel_para_linux_192_168_0_16.sh \
  linux_baixar_e_atualizar_painel_argiloteca.sh \
  argiloteca/argiloteca_custom/argiloteca/mineralogia.py \
  argiloteca/argiloteca_custom/argiloteca/services/analytical_packages.py \
  argiloteca/argiloteca_custom/argiloteca/services/drx.py \
  argiloteca/argiloteca_custom/argiloteca/services/geoquimica.py \
  argiloteca/argiloteca_custom/argiloteca/services/raw_snapshot_links.py \
  argiloteca/argiloteca_custom/argiloteca/static/css/drx-comparacao.css \
  argiloteca/argiloteca_custom/argiloteca/static/css/pacote-analitico.css \
  argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js \
  argiloteca/argiloteca_custom/argiloteca/static/js/pacote-analitico.js \
  argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/analises_index.html \
  argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/argilomineral_detail.html \
  argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/catalogo_autorizado_argilominerais.html \
  argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html \
  argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/pacote_analitico.html \
  argiloteca/argiloteca_custom/argiloteca/views.py \
  argiloteca/argiloteca_custom/tests/test_drx.py \
  argiloteca/argiloteca_custom/tests/test_raw_snapshot_links.py \
  povoamento/drx/gerar_metricas_painel_drx.py \
  povoamento/drx/baixar_webmineral_argilominerais.py \
  povoamento/drx/classificar_minerais_raw.py \
  povoamento/drx/publicar_resultado_painel_argiloteca.sh \
  povoamento/drx/reclassificar_minerais_raw.sh \
  povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_argilominerais_vocabulario.json \
  povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_xray_referencia.json \
  povoamento/visualizacao-drx/webmineral/webmineral_argilominerais_vocabulario_manifest.json

staged_files="$(git diff --cached --name-only)"
if [[ -z "$staged_files" ]]; then
  echo "Nada novo para commit; vou atualizar as branches com o HEAD atual."
else
  bad_files="$(printf '%s\n' "$staged_files" | grep -E '(^|/)(__pycache__|\\.pytest_cache|var)(/|$)|\\.(raw|RAW|rar|zip|7z|tar|gz|pyc)$|^reports/.*\\.(json|html|pdf)$' || true)"
  if [[ -n "$bad_files" ]]; then
    echo "ERRO: arquivos bloqueados entraram no staging:" >&2
    printf '%s\n' "$bad_files" >&2
    echo "Remova esses arquivos do staging antes de enviar." >&2
    exit 1
  fi

  echo "Arquivos que serao enviados:"
  printf '  %s\n' $staged_files

  echo
  echo "[7] Criando commit..."
  git commit -m "$COMMIT_MSG"
fi

if [[ "$UPDATE_MAIN" == "1" ]]; then
  echo
  echo "[8] Integrando $MAIN_BRANCH remota antes do push..."
  # A tentativa via porta 443 contorna redes que bloqueiam SSH padrao do GitHub.
  if git fetch "$REMOTE" "$MAIN_BRANCH"; then
    echo "$MAIN_BRANCH remota atualizada a partir de $REMOTE."
  else
    echo "Fetch de $MAIN_BRANCH via remote '$REMOTE' falhou."
    if [[ "$TRY_SSH_443" == "1" ]]; then
      echo "Tentando fetch de $MAIN_BRANCH pelo GitHub SSH na porta 443..."
      git fetch "$SSH_443_URL" "$MAIN_BRANCH"
    else
      echo "Tente manualmente:"
      echo "  git fetch $REMOTE $MAIN_BRANCH"
      echo "ou:"
      echo "  git fetch $SSH_443_URL $MAIN_BRANCH"
      exit 1
    fi
  fi

  if git merge-base --is-ancestor FETCH_HEAD HEAD; then
    echo "$MAIN_BRANCH remota ja esta contida no commit atual."
  else
    echo "$MAIN_BRANCH remota tem commits novos; integrando antes de atualizar o GitHub..."
    git merge --no-edit FETCH_HEAD
  fi
fi

echo
echo "[9] Enviando para GitHub..."
if git push -u "$REMOTE" "HEAD:$BRANCH"; then
  echo "Push concluido em $REMOTE/$BRANCH."
else
  echo "Push via remote '$REMOTE' falhou."
  if [[ "$TRY_SSH_443" == "1" ]]; then
    echo "Tentando GitHub SSH pela porta 443..."
    git push -u "$SSH_443_URL" "HEAD:$BRANCH"
  else
    echo "Tente manualmente:"
    echo "  git push -u $REMOTE HEAD:$BRANCH"
    echo "ou:"
    echo "  git push -u $SSH_443_URL HEAD:$BRANCH"
    exit 1
  fi
fi

if [[ "$UPDATE_MAIN" == "1" ]]; then
  echo
  echo "[10] Atualizando $MAIN_BRANCH no GitHub..."
  if git push "$REMOTE" "HEAD:$MAIN_BRANCH"; then
    echo "Branch $MAIN_BRANCH atualizada em $REMOTE/$MAIN_BRANCH."
  else
    echo "Push de $MAIN_BRANCH via remote '$REMOTE' falhou."
    if [[ "$TRY_SSH_443" == "1" ]]; then
      echo "Tentando atualizar $MAIN_BRANCH pelo GitHub SSH na porta 443..."
      git push "$SSH_443_URL" "HEAD:$MAIN_BRANCH"
    else
      echo "Tente manualmente:"
      echo "  git push $REMOTE HEAD:$MAIN_BRANCH"
      echo "ou:"
      echo "  git push $SSH_443_URL HEAD:$MAIN_BRANCH"
      exit 1
    fi
  fi

  current_branch="$(git branch --show-current)"
  if [[ "$current_branch" != "$MAIN_BRANCH" ]]; then
    if git show-ref --verify --quiet "refs/heads/$MAIN_BRANCH"; then
      if git merge-base --is-ancestor "$MAIN_BRANCH" HEAD; then
        git branch -f "$MAIN_BRANCH" HEAD
        echo "Branch local $MAIN_BRANCH alinhada com o commit enviado."
      else
        echo "AVISO: branch local $MAIN_BRANCH tem commits fora do HEAD atual; nao movi a referencia local."
      fi
    else
      git branch "$MAIN_BRANCH" HEAD
      echo "Branch local $MAIN_BRANCH criada no commit enviado."
    fi
  fi
fi

echo
echo "Concluido."
