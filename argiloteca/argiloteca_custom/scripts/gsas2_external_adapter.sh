#!/usr/bin/env bash
set -euo pipefail

ROOT="${ARGILOTECA_LOCAL:-/home/invenio/invenio-project/argiloteca-local}"
GSAS2_ROOT="${ARGILOTECA_GSAS2_ROOT:-/home/invenio/invenio-project/tools/g2main_rhel}"
PYTHON="${ARGILOTECA_GSAS2_PYTHON:-$GSAS2_ROOT/bin/python}"
SCRIPT="$ROOT/app/argiloteca_custom/scripts/gsas2_external_adapter.py"

export PYTHONPATH="${ARGILOTECA_GSAS2_PYTHONPATH:-$GSAS2_ROOT/GSAS-II}${PYTHONPATH:+:$PYTHONPATH}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/argiloteca_gsas2_mpl}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/argiloteca_gsas2_cache}"

mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME"

exec "$PYTHON" "$SCRIPT"
