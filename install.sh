#!/bin/bash
# =============================================================================
# Clified — Instalador Universal (Linux/macOS)
# =============================================================================
#
# One-liner (sem clonar o clified):
#   curl -fsSL https://raw.githubusercontent.com/maikramer/clified/main/install.sh | bash
#   curl -fsSL .../install.sh | bash -s -- --get denv          # instalar ferramenta do catálogo
#   curl -fsSL .../install.sh | bash -s -- --get mytool --repo https://github.com/x/y.git
#   curl -fsSL .../install.sh | bash -s -- --catalog           # listar ferramentas remotas
#
# Local (clone do repo, dev — editable install em .installer-venv):
#   ./install.sh [tool] [opções]
#
# Defina CLIFIED_VERSION para uma versão específica (ex.: clified==0.7.0 ou
# git+https://github.com/maikramer/clified.git@main para --edge).
# =============================================================================

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
say() { printf "%b\n" "$1"; }

# --- Detectar modo: dev (clone local) vs remoto (piped / PyPI) --------------
CLIFIED_DEV_MODE=0
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/pyproject.toml" ] && grep -q 'name = "clified"' "$SCRIPT_DIR/pyproject.toml" 2>/dev/null; then
        CLIFIED_DEV_MODE=1
    fi
fi

# =============================================================================
# Modo dev: editable install no .installer-venv (clone do repo clified)
# =============================================================================
if [ "$CLIFIED_DEV_MODE" = "1" ]; then
    export CLIFIED_ROOT="$SCRIPT_DIR"
    PYTHON_CMD="${PYTHON_CMD:-python3}"

    if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
        say "${RED}✗ Python 3 não encontrado.${NC}"; exit 1
    fi
    if ! "$PYTHON_CMD" -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
        say "${RED}✗ Python 3.10+ necessário.${NC}"; "$PYTHON_CMD" -V 2>/dev/null || true; exit 1
    fi

    if [ ! -f "$SCRIPT_DIR/tools.yaml" ] && [ -f "$SCRIPT_DIR/tools.yaml.example" ]; then
        say "${CYAN}  → Criando tools.yaml a partir do exemplo...${NC}"
        cp "$SCRIPT_DIR/tools.yaml.example" "$SCRIPT_DIR/tools.yaml"
    fi

    if ! command -v uv >/dev/null 2>&1; then
        say "${CYAN}  → Instalando uv...${NC}"
        if command -v curl >/dev/null 2>&1; then
            curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null || true
        elif command -v wget >/dev/null 2>&1; then
            wget -qO- https://astral.sh/uv/install.sh | sh 2>/dev/null || true
        fi
        [ -f "$HOME/.local/bin/uv" ] && export PATH="$HOME/.local/bin:$PATH"
    fi

    INSTALLER_VENV="$SCRIPT_DIR/.installer-venv"
    INSTALLER_PY="$INSTALLER_VENV/bin/python"

    if [ -x "$INSTALLER_PY" ] && "$INSTALLER_PY" -c "import clified, rich, yaml" 2>/dev/null; then
        :
    else
        say "${CYAN}  → Ambiente do instalador (venv + clified)...${NC}"
        if command -v uv >/dev/null 2>&1; then
            uv venv "$INSTALLER_VENV" --seed --python "$PYTHON_CMD" --clear
        else
            "$PYTHON_CMD" -m venv "$INSTALLER_VENV"
        fi
        "$INSTALLER_PY" -m pip install -q --upgrade pip
        "$INSTALLER_PY" -m pip install -q -e "$SCRIPT_DIR"
    fi

    export UV_VENV_CLEAR=1
    export UV_LINK_MODE=copy
    say "${CYAN}Clified — Instalador Universal (dev)${NC}"
    echo "================================="
    exec "$INSTALLER_PY" -m clified "$@"
fi

# =============================================================================
# Modo remoto: instalar motor do PyPI e delegar a clified-install
# =============================================================================
clified_resolve_python() {
    if [ -n "${PYTHON_CMD:-}" ] && "${PYTHON_CMD}" -m pip --version >/dev/null 2>&1; then
        printf '%s\n' "${PYTHON_CMD}"; return 0
    fi
    local c
    for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3 /usr/bin/python3; do
        command -v "$c" >/dev/null 2>&1 || continue
        "$c" -m pip --version >/dev/null 2>&1 || continue
        printf '%s\n' "$c"; return 0
    done
    say "${RED}✗ Nenhum Python 3.10+ com pip encontrado. Instale python3-full ou defina PYTHON_CMD.${NC}"
    exit 1
}

clified_install_engine() {
    # Já instalado? Não precisa de resolver Python.
    if command -v clified-install >/dev/null 2>&1; then return 0; fi

    local py
    py="$(clified_resolve_python)"
    if ! "$py" -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
        say "${RED}✗ Python 3.10+ necessário.${NC}"; exit 1
    fi
    export PYTHON_CMD="$py"

    if "$py" -c "import clified" 2>/dev/null; then return 0; fi

    local spec="${CLIFIED_VERSION:-clified}"
    say "${CYAN}A instalar o motor clified via pip ($py)...${NC}"
    if ! "$py" -m pip install --user --upgrade "$spec" 2>/dev/null; then
        say "${CYAN}  → repetir com --break-system-packages (PEP 668)...${NC}"
        "$py" -m pip install --user --break-system-packages --upgrade "$spec"
    fi

    local user_base
    user_base="$("$py" -m site --user-base 2>/dev/null || true)"
    if [ -n "$user_base" ] && [ -x "$user_base/bin/clified-install" ]; then
        export PATH="$user_base/bin:${PATH}"
    fi
}

clified_install_engine

if [ $# -eq 0 ]; then
    say "${GREEN}✓ Clified instalado.${NC} Próximos passos:"
    say "  clified-install --catalog            # listar ferramentas remotas conhecidas"
    say "  clified-install --get denv           # instalar a ferramenta denv do catálogo"
    say "  clified-install --get <t> --repo URL # instalar ferramenta de um repo arbitrário"
    say "  clified-install --list               # ferramentas de um tools.yaml local"
    exit 0
fi

if command -v clified-install >/dev/null 2>&1; then
    exec clified-install "$@"
fi
PY="${PYTHON_CMD:-python3}"
if "$PY" -c "import clified" 2>/dev/null; then
    exec "$PY" -m clified "$@"
fi
say "${RED}✗ Instalação do clified falhou.${NC}"
exit 1
