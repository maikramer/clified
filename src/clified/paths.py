"""Resolução de paths — checkout local, PyPI wheel ou config do utilizador."""

from __future__ import annotations

import os
import shutil
from importlib import metadata
from pathlib import Path


def package_dir() -> Path:
    """Directório do pacote ``clified`` instalado (wheel ou editable)."""
    return Path(__file__).resolve().parent


def bundled_dir() -> Path:
    return package_dir() / "bundled"


def bundled_path(*parts: str) -> Path:
    return bundled_dir().joinpath(*parts)


def clified_home() -> Path:
    """Config do utilizador (``~/.config/clified`` ou ``CLIFIED_HOME``)."""
    env = os.environ.get("CLIFIED_HOME", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg:
        return (Path(xdg) / "clified").resolve()
    return (Path.home() / ".config" / "clified").resolve()


def clified_root() -> Path:
    """Raiz de configuração: ``CLIFIED_ROOT`` > checkout dev > ``clified_home()``."""
    env = os.environ.get("CLIFIED_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()

    pkg = package_dir()
    for candidate in (pkg.parent.parent, pkg.parent):
        if (candidate / "pyproject.toml").is_file():
            return candidate.resolve()

    return clified_home()


def tools_yaml_path() -> Path:
    custom = os.environ.get("CLIFIED_TOOLS", "").strip()
    if custom:
        return Path(custom).expanduser().resolve()

    for candidate in (
        clified_home() / "tools.yaml",
        clified_root() / "tools.yaml",
    ):
        if candidate.is_file():
            return candidate.resolve()

    return (clified_home() / "tools.yaml").resolve()


def ensure_user_tools_yaml() -> Path:
    """Garante ``~/.config/clified/tools.yaml`` (cópia do exemplo embutido se faltar)."""
    target = clified_home() / "tools.yaml"
    if target.is_file():
        return target.resolve()

    example = bundled_path("tools.yaml.example")
    target.parent.mkdir(parents=True, exist_ok=True)
    if example.is_file():
        shutil.copy2(example, target)
    else:
        target.write_text("workspace:\n  root: ..\n  name: Workspace\n\ntools: {}\n")
    return target.resolve()


def install_all_constraints_file() -> Path | None:
    for candidate in (
        bundled_path("config", "install-all-constraints.txt"),
        clified_root() / "config" / "install-all-constraints.txt",
    ):
        if candidate.is_file() and candidate.read_text(encoding="utf-8").strip():
            return candidate.resolve()
    return None


def default_clified_yml() -> Path:
    user = clified_home() / "clified.yml"
    if user.is_file():
        return user.resolve()
    bundled = bundled_path("config", "clified.yml.example")
    if bundled.is_file():
        return bundled.resolve()
    return (clified_root() / "config" / "clified.yml").resolve()


def version() -> str:
    try:
        return metadata.version("clified")
    except metadata.PackageNotFoundError:
        return "0.0.0"
