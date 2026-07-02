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


def test_repo_clone_path_roundtrip(tmp_path: Path) -> None:
    """repo_clone_path deve round-trip no state (necessário para update/uninstall)."""
    clone = tmp_path / "sources" / "demo"
    receipt = InstallReceipt(
        kind="python",
        cli_name="demo",
        source="repo",
        repo="https://example.com/demo.git",
        ref="",
        commit="deadbeef",
        repo_clone_path=str(clone),
        artifacts=[str(tmp_path / "bin" / "demo")],
    )
    record_install("demo", receipt)
    loaded = get("demo")
    assert loaded is not None
    assert loaded.repo_clone_path == str(clone)


def test_from_dict_missing_repo_clone_path_defaults_empty() -> None:
    """Receipts antigas (sem repo_clone_path) carregam com string vazia."""
    legacy = {
        "kind": "python",
        "cli_name": "demo",
        "source": "repo",
        "repo": "https://example.com/demo.git",
        "ref": "",
        "commit": "abc",
        "tools_yaml": "",
        "project_root": "",
        "venv_path": "",
        "catalog_name": "demo",
        "install_prefix": "",
        "artifacts": [],
        "installed_at": "",
        "updated_at": "",
        "clified_version": "0.7.4",
    }
    receipt = InstallReceipt.from_dict(legacy)
    assert receipt.repo_clone_path == ""
    assert receipt.commit == "abc"
