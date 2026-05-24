"""Instaladores Clified para projectos Python, Rust e Bun."""

from .base import BaseInstaller, default_python_command
from .bun_installer import BunProjectInstaller
from .python_installer import PythonProjectInstaller
from .registry import (
    TOOLS,
    ToolKind,
    ToolSpec,
    WorkspaceConfig,
    find_workspace_root,
    get_tool,
    list_available_tools,
    load_registry,
    reset_registry,
    try_find_workspace_root,
)
from .rust_installer import RustProjectInstaller

__all__ = [
    "TOOLS",
    "BaseInstaller",
    "BunProjectInstaller",
    "PythonProjectInstaller",
    "RustProjectInstaller",
    "ToolKind",
    "ToolSpec",
    "WorkspaceConfig",
    "default_python_command",
    "find_workspace_root",
    "get_tool",
    "install_all",
    "install_tool",
    "list_available_tools",
    "load_registry",
    "reset_registry",
    "try_find_workspace_root",
]


def __getattr__(name: str) -> object:
    if name in ("install_tool", "install_all"):
        from .unified import install_all, install_tool

        return install_tool if name == "install_tool" else install_all
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
