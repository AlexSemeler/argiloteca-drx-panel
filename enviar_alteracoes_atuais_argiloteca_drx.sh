#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Projeto...........: Argiloteca - Painel de DRX
# Script............: enviar_alteracoes_atuais_argiloteca_drx.sh
#
# Descricao.........:
#   Valida, commita e envia ao GitHub as alteracoes atuais do repositorio
#   argiloteca-drx-panel-upload. O script preserva o remote existente e bloqueia
#   RAWs, caches, ambientes virtuais e artefatos pesados antes do stage.
#
# Uso...............:
#   ./enviar_alteracoes_atuais_argiloteca_drx.sh "mensagem do commit"
#
# Variaveis.........:
#   REPO_DIR=/caminho/repo
#   REMOTE=origin
#   BRANCH=main
#   RUN_TESTS=1
#   PUSH=1
#   CONFIRM=1
#
# =============================================================================

REPO_DIR="${REPO_DIR:-/home/invenio/invenio-project/argiloteca-drx-panel-upload}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-$(git -C "$REPO_DIR" branch --show-current 2>/dev/null || echo main)}"
COMMIT_MSG="${1:-${COMMIT_MSG:-Atualiza painel DRX Argiloteca}}"
RUN_TESTS="${RUN_TESTS:-1}"
PUSH="${PUSH:-1}"
CONFIRM="${CONFIRM:-1}"
PYTHON_BIN="${PYTHON_BIN:-/home/invenio/invenio-project/argiloteca-local/venvs/app-py310-l3/bin/python}"
NODE_BIN="${NODE_BIN:-node}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

cd "$REPO_DIR"

echo "============================================================"
echo "Enviar alteracoes atuais - Argiloteca DRX"
echo "============================================================"
echo "Repo:      $REPO_DIR"
echo "Remote:    $REMOTE"
echo "Branch:    $BRANCH"
echo "Mensagem:  $COMMIT_MSG"
echo "Python:    $PYTHON_BIN"
echo "Run tests: $RUN_TESTS"
echo "Push:      $PUSH"
echo "Confirm:   $CONFIRM"
echo

if [[ ! -d .git ]]; then
  echo "ERRO: $REPO_DIR nao e um repositorio Git." >&2
  exit 1
fi

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "ERRO: remote '$REMOTE' nao existe." >&2
  exit 1
fi

echo "[1] Status atual:"
git status --short
echo

if [[ "$CONFIRM" == "1" ]]; then
  echo "Este script vai adicionar ao commit todas as alteracoes rastreadas e nao rastreadas permitidas por seguranca."
  echo "Revise o status acima antes de continuar."
  read -r -p "Continuar com commit e push? [s/N] " answer
  case "$answer" in
    s|S|sim|SIM|Sim) ;;
    *)
      echo "Operacao cancelada pelo usuario."
      exit 0
      ;;
  esac
fi

echo "[2] Bloqueando arquivos que nao devem ir para o Git..."
blocked_patterns='(^|/)(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|node_modules|venvs?|\.venv|instance|data/drx/raw|raw-classificados)(/|$)|\.(raw|RAW|brml|zip|7z|rar|tar|gz|pyc|sqlite|db)$'
blocked_files="$(git ls-files --others --modified --exclude-standard | grep -E "$blocked_patterns" || true)"
if [[ -n "$blocked_files" ]]; then
  echo "ERRO: os seguintes arquivos parecem ser dados brutos, caches ou artefatos pesados:" >&2
  printf '%s\n' "$blocked_files" >&2
  echo "Ajuste .gitignore ou remova esses arquivos antes de enviar." >&2
  exit 1
fi

echo "[3] Validando diferencas..."
git diff --check
echo

echo "[4] Validando sintaxe dos arquivos alterados..."
changed_python="$(git ls-files --others --modified --exclude-standard '*.py' || true)"
if [[ -n "$changed_python" ]]; then
  while IFS= read -r py_file; do
    [[ -z "$py_file" ]] && continue
    "$PYTHON_BIN" -m py_compile "$py_file"
  done <<< "$changed_python"
fi

changed_shell="$(git ls-files --others --modified --exclude-standard '*.sh' || true)"
if [[ -n "$changed_shell" ]]; then
  while IFS= read -r script; do
    [[ -z "$script" ]] && continue
    bash -n "$script"
  done <<< "$changed_shell"
fi

changed_js="$(git ls-files --others --modified --exclude-standard '*.js' || true)"
if [[ -n "$changed_js" ]]; then
  if command -v "$NODE_BIN" >/dev/null 2>&1; then
    while IFS= read -r js_file; do
      [[ -z "$js_file" ]] && continue
      "$NODE_BIN" --check "$js_file"
    done <<< "$changed_js"
  else
    echo "AVISO: node nao encontrado; validacao JavaScript pulada."
  fi
fi
echo

if [[ "$RUN_TESTS" == "1" ]]; then
  echo "[5] Rodando testes DRX disponiveis..."
  if [[ -f argiloteca/argiloteca_custom/tests/test_drx_v3_engine.py ]]; then
    PYTHONPATH="$REPO_DIR:$REPO_DIR/argiloteca/argiloteca_custom" \
      "$PYTHON_BIN" -m unittest argiloteca/argiloteca_custom/tests/test_drx_v3_engine.py
  else
    echo "AVISO: test_drx_v3_engine.py nao encontrado; testes pulados."
  fi
else
  echo "[5] RUN_TESTS=0; testes pulados."
fi
echo

echo "[6] Adicionando alteracoes ao stage..."
git add -A

staged_files="$(git diff --cached --name-only)"
if [[ -z "$staged_files" ]]; then
  echo "Nada para commitar."
else
  echo "Arquivos no commit:"
  while IFS= read -r staged_file; do
    [[ -z "$staged_file" ]] && continue
    printf '  %s\n' "$staged_file"
  done <<< "$staged_files"
  echo
  git commit -m "$COMMIT_MSG"
fi

echo
echo "[7] Estado apos commit:"
git status --short
git log --oneline --decorate -1
echo

if [[ "$PUSH" == "1" ]]; then
  echo "[8] Enviando para $REMOTE/$BRANCH..."
  git push -u "$REMOTE" "HEAD:$BRANCH"
  echo "Push concluido."
else
  echo "[8] PUSH=0; commit local criado sem envio."
fi
