"""Paths do projecto-alvo — raiz via marcadores e ficheiros relativos.

Este módulo resolve o sistema de ficheiros do projecto que o Clified está a
instalar (não do próprio Clified): ``find_project_root`` sobe directórios até
encontrar um marcador (``pyproject.toml``, ``Cargo.toml``, ``tools.yaml``…),
e ``resolve_project_file`` devolve um ficheiro relativo a essa raiz.  Para os
paths do próprio Clified (bundled, home, root), ver ``clified.paths``.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_MARKERS: tuple[str, ...] = (
    "pyproject.toml",
    "Cargo.toml",
    "package.json",
    "pubspec.yaml",
    "tools.yaml",
    "go.mod",
)


def find_project_root(
    start: Path | str | None = None,
    *,
    markers: tuple[str, ...] = DEFAULT_MARKERS,
    max_depth: int = 12,
) -> Path | None:
    """Sobe directórios até encontrar um marcador de projecto."""
    if start is None:
        start = Path.cwd()
    current = Path(start).resolve()
    env_root = os.environ.get("CLIFIED_PROJECT_ROOT", "").strip()
    if env_root:
        p = Path(env_root).resolve()
        if p.is_dir():
            return p

    for _ in range(max_depth):
        for marker in markers:
            if (current / marker).exists():
                return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def resolve_project_file(
    relative: str | Path,
    *,
    start: Path | str | None = None,
    markers: tuple[str, ...] = DEFAULT_MARKERS,
) -> Path:
    """Resolve ficheiro relativo à raiz do projecto (CWD → markers → erro)."""
    rel = Path(relative)
    if rel.is_absolute() and rel.is_file():
        return rel.resolve()

    root = find_project_root(start, markers=markers)
    if root is not None:
        candidate = (root / rel).resolve()
        if candidate.is_file():
            return candidate

    cwd_candidate = (Path.cwd() / rel).resolve()
    if cwd_candidate.is_file():
        return cwd_candidate

    msg = (
        f"Ficheiro não encontrado: {relative!r}. "
        f"Procurei a partir de {start or Path.cwd()} com marcadores {markers}."
    )
    raise FileNotFoundError(
        msg,
    )
