"""Garantir que o Clified está disponível (PyPI ou checkout local)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def _min_version() -> str:
    try:
        from clified import __version__

        return __version__
    except ImportError:
        return "0.4.0"


def is_available() -> bool:
    if shutil.which("clified-install"):
        return True
    try:
        import clified  # noqa: F401
    except ImportError:
        return False
    else:
        return True


def install(*, user: bool = True, upgrade: bool = False) -> None:
    spec = f"clified>={_min_version()}"
    cmd = [sys.executable, "-m", "pip", "install"]
    if user:
        cmd.append("--user")
    if upgrade:
        cmd.append("--upgrade")
    cmd.append(spec)
    subprocess.run(cmd, check=True)


def runner_argv() -> list[str]:
    """Argv para invocar o CLI (``clified-install`` ou ``python -m clified``)."""
    exe = shutil.which("clified-install")
    if exe:
        return [exe]
    return [sys.executable, "-m", "clified"]


def run(argv: Sequence[str], *, cwd: str | None = None) -> int:
    if not is_available():
        install()
    cmd = [*runner_argv(), *argv]
    return subprocess.call(cmd, cwd=cwd)
