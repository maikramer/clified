"""Testes de seleção de Python."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from clified.installer.python_select import find_python_with_pip


def test_explicit_python_without_pip_raises() -> None:
    with (
        patch(
            "clified.installer.python_select._has_pip",
            return_value=False,
        ),
        pytest.raises(RuntimeError, match="sem pip"),
    ):
        find_python_with_pip("/fake/python")


def test_uses_python_cmd_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHON_CMD", "/opt/python3")
    with patch(
        "clified.installer.python_select._has_pip",
        side_effect=lambda p: p == "/opt/python3",
    ):
        assert find_python_with_pip() == "/opt/python3"


def test_falls_back_to_sys_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTHON_CMD", raising=False)
    with patch(
        "clified.installer.python_select._has_pip",
        side_effect=lambda p: p == sys.executable,
    ):
        assert find_python_with_pip() == sys.executable
