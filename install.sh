#!/bin/bash
# =============================================================================
# Clified — Instalador Universal (Linux/macOS)
# =============================================================================
#
# Uso:
#   ./install.sh <tool>       # Instalar uma ferramenta registada em tools.yaml
#   ./install.sh all          # Instalar tudo
#   ./install.sh --list       # Listar ferramentas
#
# Configure ferramentas em tools.yaml (copie de tools.yaml.example).
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CLIFIED_ROOT="$SCRIPT_DIR"
PYTHON_CMD="${PYTHON_CMD:-python3}"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

prepare_installer_environment() {
    echo -e "${CYAN}Preparando ambiente Clified...${NC}"

    if [ ! -f "$SCRIPT_DIR/tools.yaml" ]; then
        if [ -f "$SCRIPT_DIR/tools.yaml.example" ]; then
            echo -e "${CYAN}  → Criando tools.yaml a partir do exemplo...${NC}"
            cp "$SCRIPT_DIR/tools.yaml.example" "$SCRIPT_DIR/tools.yaml"
        else
            echo -e "${RED}✗ tools.yaml não encontrado em $SCRIPT_DIR${NC}"
            echo "  Copie tools.yaml.example para tools.yaml e registe as suas ferramentas."
            exit 1
        fi
    fi

    if ! command -v "$PYTHON_CMD" &> /dev/null; then
        echo -e "${RED}✗ Python 3 não encontrado.${NC}"
        exit 1
    fi

    if ! "$PYTHON_CMD" -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
        echo -e "${RED}✗ Python 3.10+ necessário.${NC}"
        "$PYTHON_CMD" -V 2>/dev/null || true
        exit 1
    fi

    if ! command -v uv &> /dev/null; then
        echo -e "${CYAN}  → Instalando uv...${NC}"
        if command -v curl &> /dev/null; then
            curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null || true
        elif command -v wget &> /dev/null; then
            wget -qO- https://astral.sh/uv/install.sh | sh 2>/dev/null || true
        fi
        if [ -f "$HOME/.local/bin/uv" ]; then
            export PATH="$HOME/.local/bin:$PATH"
            echo -e "${GREEN}  ✓ uv instalado: $(uv --version)${NC}"
        fi
    else
        echo -e "${GREEN}  ✓ uv: $(uv --version)${NC}"
    fi

    local INSTALLER_VENV="$SCRIPT_DIR/.installer-venv"
    local INSTALLER_PY="$INSTALLER_VENV/bin/python"

    if [ -x "$INSTALLER_PY" ] && "$INSTALLER_PY" -c "import clified, rich, yaml" 2>/dev/null; then
        export CLIFIED_INSTALLER_PYTHON="$INSTALLER_PY"
        return 0
    fi

    echo -e "${CYAN}  → Ambiente do instalador (venv + clified)...${NC}"

    if command -v uv &> /dev/null; then
        uv venv "$INSTALLER_VENV" --seed --python "$PYTHON_CMD" --clear
    else
        "$PYTHON_CMD" -m venv "$INSTALLER_VENV"
    fi

    if ! "$INSTALLER_PY" -m pip install -q --upgrade pip; then
        echo -e "${RED}✗ Falha ao preparar pip no venv do instalador.${NC}"
        exit 1
    fi

    if ! "$INSTALLER_PY" -m pip install -q -e "$SCRIPT_DIR"; then
        echo -e "${RED}✗ Falha ao instalar clified (pip install -e).${NC}"
        exit 1
    fi

    export CLIFIED_INSTALLER_PYTHON="$INSTALLER_PY"
}

prepare_installer_environment

export UV_VENV_CLEAR=1
export UV_LINK_MODE=copy

echo -e "${CYAN}Clified — Instalador Universal${NC}"
echo "================================="

exec "${CLIFIED_INSTALLER_PYTHON:?}" -m clified "$@"
