"""Derive Python version bounds from a project's ``requires-python``.

clified registers a coarse ``min_python`` (and optional ``max_python``) per
tool in ``tools.yaml``, but the authoritative constraint usually lives in the
tool's own ``pyproject.toml`` as ``requires-python`` (e.g.
``">=3.13,<3.14"``).  Honouring only the floor let clified happily build a
venv on a *newer* interpreter than a tool supports — the exact trap that made
a ``<3.14`` tool land on system Python 3.14 and fail to install.

This module reads ``requires-python`` (without adding a ``packaging``
dependency or relying on ``tomllib``, which is absent on 3.10) and turns the
specifier set into inclusive ``(major, minor)`` floor/ceiling bounds at minor
granularity — enough to pick a compatible interpreter.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

Bound = tuple[int, int]

_REQUIRES_RE = re.compile(
    r"""^\s*requires-python\s*=\s*["']([^"']+)["']""",
    re.MULTILINE,
)
_CLAUSE_RE = re.compile(r"(>=|<=|==|~=|!=|>|<)\s*(\d+)(?:\.(\d+))?(?:\.\*|\.\d+)?")


def read_requires_python(project_root: Path) -> str | None:
    """Return the raw ``requires-python`` string from ``pyproject.toml``.

    Scans only for the ``requires-python`` assignment so it works on any
    Python version without a TOML parser.  Returns ``None`` when the file or
    field is absent.
    """
    pyproject = project_root / "pyproject.toml"
    try:
        text = pyproject.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = _REQUIRES_RE.search(text)
    return match.group(1).strip() if match else None


def parse_specifier(specifier: str) -> tuple[Bound | None, Bound | None]:
    """Parse a ``requires-python`` specifier into ``(floor, ceiling)`` bounds.

    Both bounds are inclusive ``(major, minor)`` tuples at minor granularity,
    or ``None`` when unconstrained.  Patch-level precision is ignored.
    Unrecognised input yields ``(None, None)`` so callers fall back safely.

    Examples:
        ``">=3.13,<3.14"`` -> ``((3, 13), (3, 13))``
        ``">=3.10"``       -> ``((3, 10), None)``
        ``"==3.12.*"``     -> ``((3, 12), (3, 12))``
    """
    floor: Bound | None = None
    ceiling: Bound | None = None

    for op, major_s, minor_s in _CLAUSE_RE.findall(specifier):
        major = int(major_s)
        minor = int(minor_s) if minor_s else 0
        ver = (major, minor)
        if op == ">=":
            floor = _max_bound(floor, ver)
        elif op == ">":
            floor = _max_bound(floor, (major, minor + 1))
        elif op == "<=":
            ceiling = _min_bound(ceiling, ver)
        elif op == "<":
            # ``<3.14`` means the highest allowed minor is 3.13. With no minor
            # given (``<4``) we cannot express a minor ceiling, so skip it.
            if minor_s:
                ceiling = _min_bound(ceiling, (major, minor - 1))
        elif op in ("==", "~="):
            floor = _max_bound(floor, ver)
            if op == "==":
                ceiling = _min_bound(ceiling, ver)
        # "!=" excludes a single version; ignored at minor granularity.

    return floor, ceiling


def bounds_from_pyproject(project_root: Path) -> tuple[Bound | None, Bound | None]:
    """Read ``requires-python`` from *project_root* and return its bounds."""
    specifier = read_requires_python(project_root)
    if not specifier:
        return None, None
    return parse_specifier(specifier)


def _max_bound(current: Bound | None, candidate: Bound) -> Bound:
    return candidate if current is None or candidate > current else current


def _min_bound(current: Bound | None, candidate: Bound) -> Bound:
    return candidate if current is None or candidate < current else current
