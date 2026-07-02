"""Testes do bootstrap Clified."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from clified.installer import bootstrap


def test_pip_install_retries_with_break_system_packages() -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, *, check=False):
        calls.append(list(cmd))
        if "--break-system-packages" in cmd:
            return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=1)

    with patch("clified.installer.bootstrap.subprocess.run", side_effect=fake_run):
        bootstrap._pip_install("/usr/bin/python3", "clified>=0.4.1")

    assert len(calls) == 2
    assert "--break-system-packages" in calls[1]


def test_install_sets_python_cmd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTHON_CMD", raising=False)
    with (
        patch(
            "clified.installer.bootstrap.find_python_with_pip",
            return_value="/usr/bin/python3.14",
        ),
        patch("clified.installer.bootstrap._pip_install") as mock_pip,
    ):
        py = bootstrap.install()
    assert py == "/usr/bin/python3.14"
    mock_pip.assert_called_once()
    assert os.environ["PYTHON_CMD"] == "/usr/bin/python3.14"


def test_explicit_python_without_pip_raises() -> None:
    with (
        patch(
            "clified.installer.bootstrap._has_pip",
            return_value=False,
        ),
        pytest.raises(RuntimeError, match="sem pip"),
    ):
        bootstrap.find_python_with_pip("/fake/python")


def test_uses_python_cmd_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHON_CMD", "/opt/python3")
    with patch(
        "clified.installer.bootstrap._has_pip",
        side_effect=lambda p: p == "/opt/python3",
    ):
        assert bootstrap.find_python_with_pip() == "/opt/python3"


def test_falls_back_to_sys_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTHON_CMD", raising=False)
    with patch(
        "clified.installer.bootstrap._has_pip",
        side_effect=lambda p: p == sys.executable,
    ):
        assert bootstrap.find_python_with_pip() == sys.executable
