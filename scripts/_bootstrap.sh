#!/usr/bin/env bash
# =============================================================================
# Primitivas partilhadas de bootstrap do Clified (Python + pip install + exec).
# Sourced por scripts/install-bootstrap.sh e por install.sh de projectos
# consumidores. NÃO chama exit por si — a orquestração fica no wrapper.
#
#   source "$(dirname "${BASH_SOURCE[0]}")/_bootstrap.sh"
#   py="$(clified_resolve_python)" || exit 1
#   clified_pip_install "$py" "clified>=0.4.1"
#   clified_exec "$py" "$@"
# =============================================================================

clified_resolve_python() {
  if [[ -n "${PYTHON_CMD:-}" ]]; then
    if "${PYTHON_CMD}" -m pip --version >/dev/null 2>&1; then
      printf '%s\n' "${PYTHON_CMD}"
      return 0
    fi
    echo "PYTHON_CMD=${PYTHON_CMD} não tem pip funcional." >&2
    return 1
  fi

  local c
  for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3 /usr/bin/python3; do
    command -v "$c" >/dev/null 2>&1 || continue
    "$c" -m pip --version >/dev/null 2>&1 || continue
    printf '%s\n' "$c"
    return 0
  done

  echo "Nenhum Python com pip encontrado. Instale python3-full ou defina PYTHON_CMD." >&2
  return 1
}

clified_pip_install() {
  local py="$1" spec="$2"
  if "$py" -m pip install --user --upgrade "$spec"; then
    return 0
  fi
  echo "A repetir pip com --break-system-packages (PEP 668)…" >&2
  "$py" -m pip install --user --break-system-packages --upgrade "$spec"
}

clified_find_user_bin() {
  local py="$1"
  local user_base
  user_base="$("$py" -m site --user-base 2>/dev/null || true)"
  if [[ -n "$user_base" && -x "${user_base}/bin/clified-install" ]]; then
    printf '%s\n' "${user_base}/bin/clified-install"
  fi
}

clified_exec() {
  local py="$1"; shift
  if command -v clified-install >/dev/null 2>&1; then
    exec clified-install "$@"
  fi
  local user_bin
  user_bin="$(clified_find_user_bin "$py")"
  if [[ -n "$user_bin" ]]; then
    export PATH="$(dirname "$user_bin"):${PATH}"
    exec clified-install "$@"
  fi
  exec "$py" -m clified "$@"
}
