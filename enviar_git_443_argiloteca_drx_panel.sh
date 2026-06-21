#!/usr/bin/env bash
set -euo pipefail

# Envia a versão leve do painel DRX para o GitHub usando HTTPS na porta 443.
# O script não adiciona dados brutos, venvs, caches ou artefatos ignorados.

REPO_DIR="${REPO_DIR:-/home/invenio/invenio-project/argiloteca-drx-panel-upload}"
REMOTE_NAME="${REMOTE_NAME:-origin}"
REMOTE_URL="${REMOTE_URL:-https://github.com:443/AlexSemeler/argiloteca-drx-panel.git}"
BRANCH="${BRANCH:-main}"
COMMIT_MSG="${COMMIT_MSG:-Atualiza painel DRX Argiloteca}"
AUTO_COMMIT="${AUTO_COMMIT:-1}"
FORCE_PUSH="${FORCE_PUSH:-0}"

cd "$REPO_DIR"

echo "============================================================"
echo "Envio Git - Painel DRX Argiloteca"
echo "============================================================"
echo "Repo:       $REPO_DIR"
echo "Remote:     $REMOTE_NAME"
echo "URL:        $REMOTE_URL"
echo "Branch:     $BRANCH"
echo "Commit msg: $COMMIT_MSG"
echo "Auto commit:$AUTO_COMMIT"
echo "Force push: $FORCE_PUSH"
echo

if [[ ! -d .git ]]; then
  echo "[1] Inicializando repositorio Git local..."
  git init -b "$BRANCH"
fi

if git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  git remote set-url "$REMOTE_NAME" "$REMOTE_URL"
else
  git remote add "$REMOTE_NAME" "$REMOTE_URL"
fi

echo "[2] Conferindo remote configurado..."
git remote -v
echo

echo "[3] Checando arquivos bloqueados por seguranca..."
blocked_candidates="$(find . -type f \( \
  -iname '*.raw' -o \
  -iname '*.pyc' -o \
  -iname '*.zip' -o \
  -iname '*.tar' -o \
  -iname '*.gz' -o \
  -path '*/__pycache__/*' -o \
  -path './argiloteca-local/*' -o \
  -path './venvs/*' -o \
  -path './.venv/*' -o \
  -path './instance/*' \
\) -not -path './.git/*' -print)"

blocked_files=""
while IFS= read -r candidate; do
  [[ -z "$candidate" ]] && continue
  if git check-ignore -q "$candidate"; then
    continue
  fi
  blocked_files+="${candidate}"$'\n'
done <<< "$blocked_candidates"

if [[ -n "$blocked_files" ]]; then
  echo "ERRO: encontrei arquivos que nao devem ser enviados ao Git:" >&2
  printf '%s\n' "$blocked_files" >&2
  echo "Remova ou ignore esses arquivos antes de continuar." >&2
  exit 1
fi

echo "[4] Validando diferencas do Git..."
git diff --check
echo

if [[ "$AUTO_COMMIT" == "1" ]]; then
  echo "[5] Adicionando arquivos permitidos ao stage..."
  git add .

  staged_count="$(git diff --cached --name-only | wc -l | tr -d ' ')"
  if [[ "$staged_count" == "0" ]]; then
    echo "Nenhuma alteracao nova para commit; usando HEAD atual."
  else
    echo "Arquivos no stage: $staged_count"
    git commit -m "$COMMIT_MSG"
  fi
else
  echo "[5] AUTO_COMMIT=0; nao vou alterar stage nem criar commit."
fi

echo
echo "[6] Estado local:"
git status --short
git log --oneline --decorate -1
echo

echo "[7] Enviando para GitHub via HTTPS/443..."
if [[ "$FORCE_PUSH" == "1" ]]; then
  echo "Modo FORCE_PUSH=1: usando --force-with-lease."
  git push --force-with-lease -u "$REMOTE_NAME" "HEAD:$BRANCH"
else
  git push -u "$REMOTE_NAME" "HEAD:$BRANCH"
fi

echo
echo "Envio concluido."
