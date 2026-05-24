"""Testes hooks reutilizáveis."""

from __future__ import annotations

from clified.hooks import noop, pip_check


def test_noop_returns_true() -> None:
    assert noop(object()) is True


def test_pip_check_importable() -> None:
    assert callable(pip_check)
