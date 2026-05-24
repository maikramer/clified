"""Seleccionar um interpretador Python com pip funcional."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


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
