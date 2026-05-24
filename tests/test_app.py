"""Testes scaffold Click."""

from __future__ import annotations

import pytest

from clified.cli.app import require_click


def test_require_click_raises_without_click(monkeypatch: pytest.MonkeyPatch) -> None:
    import clified.cli.app as app_mod

    monkeypatch.setattr(app_mod, "click", None)
    with pytest.raises(ImportError, match="Click não instalado"):
        require_click()


def test_create_cli_group_with_click() -> None:
    pytest.importorskip("click")
    from clified.cli.app import create_cli_group

    group = create_cli_group("testcli", "Test CLI")
    assert group.name == "testcli"
