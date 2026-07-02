"""Tests for absolutising relative file: dependency URLs during uv builds."""

from __future__ import annotations

from pathlib import Path

import pytest

from clified.installer.python_installer import (
    _patched_relative_deps,
    _rewrite_relative_file_deps,
)


class _BoomError(Exception):
    """Sentinel error for context-manager restore-on-failure tests."""


def test_rewrite_relative_file_dep(tmp_path: Path) -> None:
    (tmp_path / "Shared").mkdir()
    text = (
        'dependencies = [\n  "gamedev-shared @ file:../Shared",\n  "trimesh>=4",\n]\n'
    )
    out, changed = _rewrite_relative_file_deps(text, tmp_path / "Tool")
    assert changed
    expected = (tmp_path / "Shared").resolve()
    # Proper file URL: file:///C:/.../Shared (3 slashes, forward slashes).
    # The malformed ``file://C:\...`` (2 slashes + backslashes) is rejected by uv.
    assert f"@ file:///{expected.as_posix()}" in out
    assert "trimesh>=4" in out
    assert "file:../Shared" not in out


def test_rewrite_skips_absolute_and_normal(tmp_path: Path) -> None:
    text = 'dependencies = [\n  "pkg @ file:///opt/pkg",\n  "rich>=13",\n]\n'
    out, changed = _rewrite_relative_file_deps(text, tmp_path)
    assert not changed
    assert out == text


def test_patched_relative_deps_restores(tmp_path: Path) -> None:
    proj = tmp_path / "Tool"
    proj.mkdir()
    (tmp_path / "Shared").mkdir()
    original = 'dependencies = ["gamedev-shared @ file:../Shared"]\n'
    pyproject = proj / "pyproject.toml"
    pyproject.write_text(original, encoding="utf-8")

    inside = {}
    with _patched_relative_deps(proj, _NullLogger()):
        inside["text"] = pyproject.read_text(encoding="utf-8")

    # Patched while inside the context, restored verbatim afterwards.
    assert "file:../Shared" not in inside["text"]
    assert pyproject.read_text(encoding="utf-8") == original


def test_patched_relative_deps_restores_on_error(tmp_path: Path) -> None:
    proj = tmp_path / "Tool"
    proj.mkdir()
    (tmp_path / "Shared").mkdir()
    original = 'dependencies = ["gamedev-shared @ file:../Shared"]\n'
    pyproject = proj / "pyproject.toml"
    pyproject.write_text(original, encoding="utf-8")

    with pytest.raises(_BoomError), _patched_relative_deps(proj, _NullLogger()):
        raise _BoomError
    assert pyproject.read_text(encoding="utf-8") == original


def test_patched_relative_deps_noop_without_file_deps(tmp_path: Path) -> None:
    proj = tmp_path / "Tool"
    proj.mkdir()
    original = 'dependencies = ["rich>=13"]\n'
    (proj / "pyproject.toml").write_text(original, encoding="utf-8")
    with _patched_relative_deps(proj, _NullLogger()):
        pass
    assert (proj / "pyproject.toml").read_text(encoding="utf-8") == original


class _NullLogger:
    def info(self, *_a: object, **_k: object) -> None: ...
    def step(self, *_a: object, **_k: object) -> None: ...
