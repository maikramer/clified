#!/usr/bin/env bash
# Bootstrap Clified (PyPI) — wrapper fino sobre scripts/_bootstrap.sh.
# Sourced por install.sh dos projectos consumidores.
#
# Uso:
#   source "$(dirname "$0")/scripts/install-bootstrap.sh"
#   clified_bootstrap ai2print "$@"

# shellcheck source=_bootstrap.sh
source "$(dirname "${BASH_SOURCE[0]}")/_bootstrap.sh"

clified_bootstrap() {
  local min_ver="${CLIFIED_MIN_VERSION:-0.4.1}"

  # Já instalado? Não precisa de resolver Python.
  if command -v clified-install >/dev/null 2>&1; then
    exec clified-install "$@"
  fi

  local py
  py="$(clified_resolve_python)" || return 1
  export PYTHON_CMD="$py"

  if "$py" -c "import clified" 2>/dev/null; then
    exec "$py" -m clified "$@"
  fi

  echo "A instalar clified>=${min_ver} via pip (${py})…" >&2
  clified_pip_install "$py" "clified>=${min_ver}" || return 1

  clified_exec "$py" "$@"
}
