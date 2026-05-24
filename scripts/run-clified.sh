#!/bin/bash
# Executa o Clified via PyPI (clified-install) ou checkout local (dev).
set -euo pipefail

PYTHON_CMD="${PYTHON_CMD:-python3}"
MIN_VERSION="${CLIFIED_MIN_VERSION:-0.4.0}"

if command -v clified-install &>/dev/null; then
  exec clified-install "$@"
fi

if "$PYTHON_CMD" -c "import clified" 2>/dev/null; then
  exec "$PYTHON_CMD" -m clified "$@"
fi

echo "Clified não encontrado — a instalar via pip (>= ${MIN_VERSION})..."
if ! "$PYTHON_CMD" -m pip install --user --upgrade "clified>=${MIN_VERSION}"; then
  echo "Falha ao instalar clified. Tente: pip install clified" >&2
  exit 1
fi

if command -v clified-install &>/dev/null; then
  exec clified-install "$@"
fi

USER_BASE="$("$PYTHON_CMD" -m site --user-base  2>/dev/null || true)"
if [[ -n "$USER_BASE" && -x "$USER_BASE/bin/clified-install" ]]; then
  exec "$USER_BASE/bin/clified-install" "$@"
fi

exec "$PYTHON_CMD" -m clified "$@"
