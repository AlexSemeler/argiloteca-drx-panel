#!/usr/bin/env bash
set -euo pipefail

ROOT="${ARGILOTECA_LOCAL:-/home/invenio/invenio-project/argiloteca-local}"
PYTHON="${ARGILOTECA_DARA_PYTHON:-$ROOT/venvs/dara-xrd-py310/bin/python}"
SCRIPT="$ROOT/app/argiloteca_custom/scripts/dara_external_adapter.py"

export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/argiloteca_mplconfig}"
mkdir -p "$MPLCONFIGDIR"

exec "$PYTHON" "$SCRIPT"
