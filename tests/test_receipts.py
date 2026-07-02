"""Testes de receipts (state file de instalações)."""

from __future__ import annotations

from pathlib import Path

import pytest

from clified.core.state_store import get_state_store
from clified.installer.receipts import (
    InstallReceipt,
    get,
    list_with_status,
    load_all,
    record_install,
    remove,
    reset_store,
    verify,
)


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    reset_store()
    home = tmp_path / "home"
    home.mkdir()
    state = home / "state.json"
    monkeypatch.setenv("CLIFIED_HOME", str(home))
    get_state_store(state, reset=True)
    return state


def test_record_and_load() -> None:
    receipt = InstallReceipt(
        kind="python",
        cli_name="text2d",
        source="catalog",
        repo="https://github.com/x/GameDev.git",
        commit="abc123def",
        artifacts=["/tmp/bin/text2d"],
    )
    record_install("text2d", receipt)
    loaded = get("text2d")
    assert loaded is not None
    assert loaded.cli_name == "text2d"
    assert loaded.commit == "abc123def"
    assert "text2d" in load_all()


def test_verify_ok_and_broken(tmp_path: Path) -> None:
    wrapper = tmp_path / "text2d"
    wrapper.write_text("#!/bin/sh", encoding="utf-8")
    receipt = InstallReceipt(
        kind="python",
        cli_name="text2d",
        source="local",
        artifacts=[str(wrapper)],
    )
    assert verify(receipt) == "ok"
    wrapper.unlink()
    assert verify(receipt) == "broken"


def test_remove() -> None:
    record_install(
        "demo",
        InstallReceipt(kind="python", cli_name="demo", source="local"),
    )
    assert remove("demo") is True
    assert get("demo") is None


def test_list_with_status() -> None:
    record_install(
        "demo",
        InstallReceipt(kind="python", cli_name="demo", source="catalog"),
    )
    rows = list_with_status()
    assert len(rows) == 1
    assert rows[0]["name"] == "demo"
