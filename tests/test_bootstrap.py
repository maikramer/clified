"""Testes do bootstrap Clified."""

from __future__ import annotations

import os
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
