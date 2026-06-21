#!/usr/bin/env bash
set -euo pipefail

ROOT="${ARGILOTECA_LOCAL:-/home/invenio/invenio-project/argiloteca-local}"
PYTHON="${ARGILOTECA_GSAS2_PYTHON:-$ROOT/venvs/drx-science-py310/bin/python}"
SCRIPT="$ROOT/app/argiloteca_custom/scripts/gsas2_external_adapter.py"

exec "$PYTHON" "$SCRIPT"
