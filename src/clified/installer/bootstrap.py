"""Garantir que o Clified está disponível (PyPI ou checkout local).

Inclui a selecção de interpretador Python com pip funcional — lógica que
vivia em ``python_select.py`` e agora está consolidada aqui.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from clified.installer.base import prepend_path_env

if TYPE_CHECKING:
    from collections.abc import Sequence


def _has_pip(python: str) -> bool:
    try:
        subprocess.run(
            [python, "-m", "pip", "--version"],
            capture_output=True,
            check=True,
            timeout=15,
        )
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
        OSError,
    ):
        return False
    else:
        return True


def _candidate_pythons() -> list[str]:
    if platform.system().lower() == "windows":
        return ["python", "python3"]
    return [
        "python3.14",
        "python3.13",
        "python3.12",
        "python3.11",
        "python3.10",
        "python3",
        "/usr/bin/python3",
    ]


def find_python_with_pip(explicit: str | None = None) -> str:
    """Devolve o primeiro Python com ``pip`` disponível.

    Ordem: ``explicit`` → ``PYTHON_CMD`` → candidatos comuns → ``sys.executable``.
    """
    if explicit and explicit.strip():
        py = explicit.strip()
        if not _has_pip(py):
            msg = f"Python sem pip funcional: {py}"
            raise RuntimeError(msg)
        return py

    env = os.environ.get("PYTHON_CMD", "").strip()
    if env and _has_pip(env):
        return env

    seen: set[str] = set()
    ordered: list[str] = []
    if sys.executable:
        ordered.append(sys.executable)
    ordered.extend(_candidate_pythons())

    for raw in ordered:
        if not raw or raw in seen:
            continue
        seen.add(raw)
        path = raw if Path(raw).is_absolute() else shutil.which(raw)
        if path and _has_pip(path):
            return path

    if sys.executable and _has_pip(sys.executable):
        return sys.executable

    msg = (
        "Nenhum Python com pip encontrado. "
        "Instale python3-full (Debian/Ubuntu) ou defina PYTHON_CMD."
    )
    raise RuntimeError(msg)


def _min_version() -> str:
    try:
        from clified import __version__

        return __version__
    except ImportError:
        return "0.5.0"


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


def _user_script_dirs(python: str) -> list[Path]:
    """Directorias onde ``pip install --user`` coloca executáveis (``clified-install``)."""
    dirs: list[Path] = []
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
    else:
        user_base = user_base or ""

    if user_base:
        sub = "Scripts" if sys.platform == "win32" else "bin"
        dirs.append(Path(user_base) / sub)

    if sys.platform == "win32":
        try:
            import sysconfig

            nt_user = sysconfig.get_path("scripts", "nt_user")
            if nt_user:
                dirs.append(Path(nt_user))
        except (ImportError, KeyError):
            pass

    seen: set[str] = set()
    unique: list[Path] = []
    for d in dirs:
        key = str(d.resolve()) if d.exists() else str(d)
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def _user_scripts_bin(python: str) -> str | None:
    for parent in _user_script_dirs(python):
        candidate = parent / "clified-install"
        if candidate.is_file() or shutil.which(str(candidate)):
            return str(candidate)
    return None


def run(argv: Sequence[str], *, cwd: str | None = None) -> int:
    if not is_available():
        python = install()
        for parent in _user_script_dirs(python):
            if parent.is_dir():
                prepend_path_env(parent, is_windows=sys.platform == "win32")
                break
    cmd = [*runner_argv(), *argv]
    return subprocess.call(cmd, cwd=cwd)
