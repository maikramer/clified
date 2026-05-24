"""Hooks reutilizáveis para tools.yaml."""

from .mcp import register_mcp, register_mcp_serve
from .pytorch import install_nvdiffrast, pip_check
from .skills import register_cursor_skill

__all__ = [
    "install_nvdiffrast",
    "noop",
    "pip_check",
    "register_cursor_skill",
    "register_mcp",
    "register_mcp_serve",
]


def noop(_installer: object) -> bool:
    return True
