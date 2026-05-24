"""Garantir que o Clified está disponível (PyPI ou checkout local)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .python_select import find_python_with_pip

if TYPE_CHECKING:
    from collections.abc import Sequence


def _min_version() -> str:
    try:
        from clified import __version__

        return __version__
    except ImportError:
        return "0.4.1"


def is_available() -> bool:
    if shutil.which("clified-install"):
        return True
    try:
        import clified  # noqa: F401
    except ImportError:
        return False
    else:
        return True


def _pip_install(
    python: str,
    spec: str,
    *,
    user: bool = True,
    upgrade: bool = False,
) -> None:
    cmd = [python, "-m", "pip", "install"]
    if user:
        cmd.append("--user")
    if upgrade:
        cmd.append("--upgrade")
    cmd.append(spec)

    first = subprocess.run(cmd, check=False)
    if first.returncode == 0:
        return

    retry = [python, "-m", "pip", "install"]
    if user:
        retry.append("--user")
    retry.append("--break-system-packages")
    if upgrade:
        retry.append("--upgrade")
    retry.append(spec)
    subprocess.run(retry, check=True)


def install(*, user: bool = True, upgrade: bool = False) -> str:
    """Instala clified via pip; devolve o Python usado."""
    python = find_python_with_pip()
    os.environ.setdefault("PYTHON_CMD", python)
    spec = f"clified>={_min_version()}"
    _pip_install(python, spec, user=user, upgrade=upgrade)
    return python


def runner_argv(python: str | None = None) -> list[str]:
    """Argv para invocar o CLI (``clified-install`` ou ``python -m clified``)."""
    exe = shutil.which("clified-install")
    if exe:
        return [exe]
    py = python or find_python_with_pip()
    return [py, "-m", "clified"]


def _user_scripts_bin(python: str) -> str | None:
    try:
        import site

        user_base = site.getuserbase()
    except (AttributeError, ImportError):
        proc = subprocess.run(
            [python, "-m", "site", "--user-base"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        user_base = proc.stdout.strip()
    if not user_base:
        return None
    sub = "Scripts" if sys.platform == "win32" else "bin"
    candidate = Path(user_base) / sub / "clified-install"
    if candidate.is_file() or shutil.which(str(candidate)):
        return str(candidate)
    return None


def run(argv: Sequence[str], *, cwd: str | None = None) -> int:
    if not is_available():
        python = install()
        user_bin = _user_scripts_bin(python)
        if user_bin:
            bin_dir = str(Path(user_bin).parent)
            path = os.environ.get("PATH", "")
            if bin_dir not in path.split(os.pathsep):
                os.environ["PATH"] = f"{bin_dir}{os.pathsep}{path}"
    cmd = [*runner_argv(), *argv]
    return subprocess.call(cmd, cwd=cwd)
