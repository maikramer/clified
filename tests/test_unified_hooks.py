"""Testes de hooks e ordenação do instalador unificado."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from clified.installer import registry as reg
from clified.installer.unified import (
    _install_all_sort_key,
    _run_hook,
    _run_post_install,
)


def test_run_hook_noop() -> None:
    """Hook ``noop`` devolve sucesso."""
    installer = SimpleNamespace()
    assert _run_hook("clified.hooks:noop", installer) is True


def test_run_hook_invalid_format() -> None:
    """Formato inválido falha sem excepção."""
    assert _run_hook("invalid-hook", SimpleNamespace()) is False


def test_run_hook_missing_module() -> None:
    """Módulo inexistente falha graciosamente."""
    assert _run_hook("nao.existe.modulo:func", SimpleNamespace()) is False


def test_run_hook_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hook que devolve ``False`` propaga falha."""
    def fail_hook(_installer: object) -> bool:
        return False

    import clified.installer.unified as unified_mod

    fake_mod = SimpleNamespace(fail_hook=fail_hook)
    monkeypatch.setattr(unified_mod.importlib, "import_module", lambda _path: fake_mod)
    assert _run_hook("fake:fail_hook", SimpleNamespace()) is False


def test_run_hook_imports_from_project_root(tmp_path: Path) -> None:
    """Hook local no ``project_root`` é importável."""
    (tmp_path / "hook_mod.py").write_text(
        "def run(installer):\n    installer.called = True\n    return True\n",
        encoding="utf-8",
    )
    installer = SimpleNamespace(project_root=tmp_path, called=False)
    assert _run_hook("hook_mod:run", installer) is True
    assert installer.called is True


def test_run_post_install_empty() -> None:
    """``post_install`` vazio é no-op."""
    spec = SimpleNamespace(post_install="")
    assert _run_post_install(spec, SimpleNamespace()) is True  # type: ignore[arg-type]


def test_install_all_sort_key_respects_install_order() -> None:
    """``install_order`` menor corre primeiro."""
    low = reg.ToolSpec(
        key="a",
        name="A",
        kind=reg.ToolKind.PYTHON,
        folder="a",
        cli_name="a",
        description="",
        install_order=-5,
    )
    high = reg.ToolSpec(
        key="b",
        name="B",
        kind=reg.ToolKind.RUST,
        folder="b",
        cli_name="b",
        description="",
        install_order=10,
    )
    assert _install_all_sort_key(low) < _install_all_sort_key(high)


def test_install_all_sort_key_pytorch_before_rust() -> None:
    """Projectos PyTorch precedem Rust quando empate."""
    pytorch = reg.ToolSpec(
        key="ml",
        name="ML",
        kind=reg.ToolKind.PYTHON,
        folder="ml",
        cli_name="ml",
        description="",
        needs_pytorch=True,
    )
    rust = reg.ToolSpec(
        key="rs",
        name="RS",
        kind=reg.ToolKind.RUST,
        folder="rs",
        cli_name="rs",
        description="",
    )
    assert _install_all_sort_key(pytorch) < _install_all_sort_key(rust)
