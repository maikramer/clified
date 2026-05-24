"""Testes de diagnóstico por padrões."""

from __future__ import annotations

from pathlib import Path

import pytest

from clified.patterns.loader import ErrorPatternLoader


@pytest.fixture
def loader() -> ErrorPatternLoader:
    patterns_dir = Path(__file__).resolve().parents[1] / "src" / "clified" / "patterns"
    return ErrorPatternLoader(patterns_dir)


def test_diagnose_python_missing_module(loader: ErrorPatternLoader) -> None:
    diag = loader.get_diagnosis("ModuleNotFoundError: No module named 'foo'")
    assert diag is not None
    assert diag["category"] == "dependency"
    assert "Python" in diag["diagnosis"]


def test_detect_service_build(loader: ErrorPatternLoader) -> None:
    assert loader.detect_service("error: failed to compile rustc") == "build"


def test_analyze_log_returns_matches(loader: ErrorPatternLoader) -> None:
    matches = loader.analyze_log("externally-managed-environment", service="python")
    assert matches
    assert matches[0].pattern.category == "permission"


def test_list_services(loader: ErrorPatternLoader) -> None:
    services = loader.list_services()
    names = {s.name for s in services}
    assert "base" in names or "python" in names or "build" in names
