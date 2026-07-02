"""Runtime defaults em main(): UTF-8 Windows + auto não-interativo."""

from __future__ import annotations

import argparse
import os

import pytest

from clified.installer.unified import _apply_runtime_defaults


def _ns() -> argparse.Namespace:
    return argparse.Namespace(yes=False)


class _FakeStdin:
    def __init__(self, *, isatty: bool) -> None:
        self._isatty = isatty

    def isatty(self) -> bool:
        return self._isatty


def test_non_tty_implies_yes_and_non_interactive_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("clified.installer.unified.sys.stdin", _FakeStdin(isatty=False))
    for key in ("PIP_NO_INPUT", "UV_NO_PROGRESS", "PIP_DISABLE_PIP_VERSION_CHECK"):
        monkeypatch.delenv(key, raising=False)
    args = _ns()
    _apply_runtime_defaults(args)
    assert args.yes is True
    assert os.environ.get("PIP_NO_INPUT") == "1"
    assert os.environ.get("UV_NO_PROGRESS") == "1"
    assert os.environ.get("PIP_DISABLE_PIP_VERSION_CHECK") == "1"


def test_tty_keeps_yes_false_and_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("clified.installer.unified.sys.stdin", _FakeStdin(isatty=True))
    monkeypatch.delenv("PIP_NO_INPUT", raising=False)
    args = _ns()
    _apply_runtime_defaults(args)
    assert args.yes is False
    assert "PIP_NO_INPUT" not in os.environ


def test_windows_sets_pythonutf8(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("clified.installer.unified.platform.system", lambda: "Windows")
    monkeypatch.setattr("clified.installer.unified.sys.stdin", _FakeStdin(isatty=True))
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    _apply_runtime_defaults(_ns())
    assert os.environ.get("PYTHONUTF8") == "1"
