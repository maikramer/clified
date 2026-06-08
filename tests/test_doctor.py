"""Tests for the doctor diagnostics."""

from __future__ import annotations

from pathlib import Path

from clified.installer.doctor import (
    FAIL,
    OK,
    WARN,
    _effective_bounds,
    _worse,
    diagnose_tool,
    fix_shadows,
)
from clified.installer.registry import ToolKind, ToolSpec, WorkspaceConfig


def _spec(folder: str, **kw) -> ToolSpec:
    return ToolSpec(
        key="demo",
        name="Demo",
        kind=ToolKind.PYTHON,
        folder=folder,
        cli_name="demo",
        description="",
        python_module="demo",
        **kw,
    )


def _workspace(root: Path) -> WorkspaceConfig:
    return WorkspaceConfig(root=root, name="ws")


def test_worse_ranking() -> None:
    assert _worse(OK, WARN) == WARN
    assert _worse(FAIL, WARN) == FAIL
    assert _worse(WARN, OK) == WARN


def test_effective_bounds_merges_pyproject(tmp_path: Path) -> None:
    proj = tmp_path / "Demo"
    proj.mkdir()
    (proj / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.13,<3.14"\n', encoding="utf-8"
    )
    floor, ceiling = _effective_bounds(_spec("Demo", min_python=(3, 10)), proj)
    assert floor == (3, 13)
    assert ceiling == (3, 13)


def test_diagnose_missing_project(tmp_path: Path) -> None:
    spec = _spec("Nope")
    report = diagnose_tool(spec, _workspace(tmp_path), tmp_path / "bin")
    assert report["status"] == FAIL
    assert not report["project_exists"]


def test_diagnose_missing_venv(tmp_path: Path) -> None:
    proj = tmp_path / "Demo"
    proj.mkdir()
    (proj / "pyproject.toml").write_text('[project]\nname="demo"\n', encoding="utf-8")
    report = diagnose_tool(_spec("Demo"), _workspace(tmp_path), tmp_path / "bin")
    assert report["status"] == FAIL
    assert any("venv" in i for i in report["issues"])


def test_diagnose_wrapper_shadowed(tmp_path: Path, monkeypatch) -> None:
    proj = tmp_path / "Demo"
    proj.mkdir()
    (proj / "pyproject.toml").write_text('[project]\nname="demo"\n', encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "demo"
    wrapper.write_text("#!/bin/sh\n", encoding="utf-8")

    # PATH resolves the CLI to a *different* location than our wrapper.
    monkeypatch.setattr(
        "clified.installer.doctor.shutil.which",
        lambda name: "/somewhere/else/demo" if name == "demo" else None,
    )
    report = diagnose_tool(_spec("Demo"), _workspace(tmp_path), bin_dir)
    assert report["status"] == FAIL
    assert any("ofuscado" in i for i in report["issues"])


def test_diagnose_warn_when_wrapper_missing(tmp_path: Path, monkeypatch) -> None:
    proj = tmp_path / "Demo"
    proj.mkdir()
    (proj / "pyproject.toml").write_text('[project]\nname="demo"\n', encoding="utf-8")
    # No venv (FAIL already) but ensure wrapper-missing path produces an issue.
    monkeypatch.setattr(
        "clified.installer.doctor.shutil.which",
        lambda _name: None,
    )
    report = diagnose_tool(_spec("Demo"), _workspace(tmp_path), tmp_path / "bin")
    assert any("wrapper" in i for i in report["issues"])
    assert report["status"] in (WARN, FAIL)


def test_fix_shadows_removes_earlier_path_entry(tmp_path: Path, monkeypatch) -> None:
    canonical = tmp_path / "local" / "bin"
    canonical.mkdir(parents=True)
    (canonical / "demo").write_text("#!/bin/sh\n", encoding="utf-8")
    shadow_dir = tmp_path / "stale" / "bin"
    shadow_dir.mkdir(parents=True)
    shadow = shadow_dir / "demo"
    shadow.write_text("#!/bin/sh\n", encoding="utf-8")

    import os

    monkeypatch.setenv("PATH", os.pathsep.join([str(shadow_dir), str(canonical)]))
    report = {
        "name": "demo",
        "wrapper": str(canonical / "demo"),
        "wrapper_exists": True,
    }
    removed = fix_shadows(report, _NullLogger())
    assert removed == [str(shadow)]
    assert not shadow.exists()
    assert (canonical / "demo").exists()  # canonical wrapper preserved


def test_fix_shadows_noop_without_wrapper(tmp_path: Path) -> None:
    report = {
        "name": "demo",
        "wrapper": str(tmp_path / "demo"),
        "wrapper_exists": False,
    }
    assert fix_shadows(report, _NullLogger()) == []


class _NullLogger:
    def success(self, *_a: object, **_k: object) -> None: ...
    def warning(self, *_a: object, **_k: object) -> None: ...
    def info(self, *_a: object, **_k: object) -> None: ...
