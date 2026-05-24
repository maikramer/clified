"""Testes hooks PyTorch."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from clified.hooks.pytorch import install_nvdiffrast, pip_check


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def step(self, msg: str) -> None:
        self.messages.append(msg)

    def success(self, msg: str) -> None:
        self.messages.append(msg)

    def warn(self, msg: str) -> None:
        self.messages.append(msg)

    def warning(self, msg: str) -> None:
        self.warn(msg)

    def error(self, msg: str) -> None:
        self.messages.append(msg)


def test_install_nvdiffrast_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_NVDIFFRAST", "1")
    logger = _Logger()
    installer = SimpleNamespace(logger=logger, venv_python="/venv/bin/python", project_root="/proj")
    assert install_nvdiffrast(installer) is True
    assert any("SKIP_NVDIFFRAST" in m for m in logger.messages)


def test_pip_check_success(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = _Logger()
    installer = SimpleNamespace(
        logger=logger,
        venv_python="/venv/bin/python",
        project_root="/proj",
    )
    mock_run = MagicMock()
    monkeypatch.setattr("clified.hooks.pytorch.subprocess.run", mock_run)
    monkeypatch.setattr("clified.hooks.pytorch.has_uv", lambda: False)

    assert pip_check(installer) is True
    mock_run.assert_called_once()


def test_pip_check_conflict_still_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    logger = _Logger()
    installer = SimpleNamespace(
        logger=logger,
        venv_python="/venv/bin/python",
        project_root="/proj",
    )

    def boom(*_args, **_kwargs) -> None:
        raise subprocess.CalledProcessError(1, "pip")

    monkeypatch.setattr("clified.hooks.pytorch.subprocess.run", boom)
    monkeypatch.setattr("clified.hooks.pytorch.has_uv", lambda: False)

    assert pip_check(installer) is True
    assert any("pip check" in m for m in logger.messages)
