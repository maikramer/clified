"""Testes do módulo installer/unified.py (funções públicas)."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clified.installer import registry as reg
from clified.installer.unified import (
    _diagnose_failure,
    _install_all_sort_key,
    _run_hook,
    _run_with_retry,
    install_all,
    install_tool,
)


def _setup_tools_yaml(
    clified_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    content: str,
) -> Path:
    path = clified_root / "tools.yaml"
    path.write_text(content.strip(), encoding="utf-8")
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(path))
    return path


class TestDiagnoseFailure:
    def test_no_crash_on_exception(self) -> None:
        with patch(
            "clified.installer.unified.get_pattern_loader",
            side_effect=Exception("boom"),
        ):
            _diagnose_failure("something failed", MagicMock())

    def test_successful_diagnosis(self) -> None:
        loader_mock = MagicMock()
        loader_mock.get_diagnosis.return_value = {
            "diagnosis": "bad pip",
            "solutions": ["upgrade pip"],
        }
        with patch(
            "clified.installer.unified.get_pattern_loader", return_value=loader_mock
        ):
            logger = MagicMock()
            _diagnose_failure("error occurred", logger)
        logger.warn.assert_called()

    def test_no_diagnosis_available(self) -> None:
        loader_mock = MagicMock()
        loader_mock.get_diagnosis.return_value = None
        with patch(
            "clified.installer.unified.get_pattern_loader", return_value=loader_mock
        ):
            logger = MagicMock()
            _diagnose_failure("error", logger)
        logger.warn.assert_not_called()


class TestRunWithRetry:
    def test_success_without_retry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CLIFIED_RETRY", raising=False)
        logger = MagicMock()
        result = _run_with_retry("install", lambda: True, logger)
        assert result is True

    def test_failure_without_retry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CLIFIED_RETRY", raising=False)
        logger = MagicMock()
        result = _run_with_retry("install", lambda: False, logger)
        assert result is False

    def test_retry_enabled_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLIFIED_RETRY", "1")
        mock_engine = MagicMock()
        mock_result = MagicMock(success=True)
        mock_engine.execute.return_value = mock_result
        with patch("clified.installer.unified.RetryEngine", return_value=mock_engine):
            result = _run_with_retry("install", lambda: True, MagicMock())
        assert result is True

    def test_explicit_max_attempts_1_skips_engine(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLIFIED_RETRY", "1")
        calls = 0

        def func() -> bool:
            nonlocal calls
            calls += 1
            return True

        with patch("clified.installer.unified.RetryEngine") as mock_engine:
            result = _run_with_retry("install", func, MagicMock(), max_attempts=1)
        assert result is True
        assert calls == 1
        mock_engine.assert_not_called()

    def test_explicit_max_attempts_uses_engine(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CLIFIED_RETRY", raising=False)
        mock_engine = MagicMock()
        mock_result = MagicMock(success=True)
        mock_engine.execute.return_value = mock_result
        with patch("clified.installer.unified.RetryEngine", return_value=mock_engine):
            result = _run_with_retry(
                "install", lambda: True, MagicMock(), max_attempts=3
            )
        assert result is True
        mock_engine.execute.assert_called_once()


class TestRunHook:
    def test_empty_hook_returns_true(self) -> None:
        assert _run_hook("", MagicMock()) is True

    def test_invalid_hook_no_colon(self) -> None:
        assert _run_hook("invalid_hook", MagicMock()) is False

    def test_hook_execution_success(self) -> None:
        mock_mod = MagicMock()
        mock_func = MagicMock(return_value=True)
        mock_mod.my_func = mock_func
        installer = MagicMock()
        installer.shared_python = None
        installer.project_root = None
        with patch(
            "clified.installer.unified.importlib.import_module", return_value=mock_mod
        ):
            result = _run_hook("my_module:my_func", installer)
        assert result is True

    def test_hook_execution_failure(self) -> None:
        mock_mod = MagicMock()
        mock_mod.my_func = MagicMock(side_effect=RuntimeError("hook error"))
        installer = MagicMock()
        installer.shared_python = None
        installer.project_root = None
        with patch(
            "clified.installer.unified.importlib.import_module", return_value=mock_mod
        ):
            result = _run_hook("my_module:my_func", installer)
        assert result is False


class TestInstallAllSortKey:
    def test_explicit_order(self) -> None:
        spec = reg.ToolSpec(
            key="demo",
            name="Demo",
            kind=reg.ToolKind.PYTHON,
            folder="demo",
            cli_name="demo",
            description="test",
            install_order=5,
        )
        key = _install_all_sort_key(spec)
        assert key[0] == 5

    def test_pytorch_rank(self) -> None:
        spec = reg.ToolSpec(
            key="demo",
            name="Demo",
            kind=reg.ToolKind.PYTHON,
            folder="demo",
            cli_name="demo",
            description="test",
            needs_pytorch=True,
        )
        key = _install_all_sort_key(spec)
        assert key[0] == 0

    def test_rust_rank(self) -> None:
        spec = reg.ToolSpec(
            key="demo",
            name="Demo",
            kind=reg.ToolKind.RUST,
            folder="demo",
            cli_name="demo",
            description="test",
        )
        key = _install_all_sort_key(spec)
        assert key[0] == 2

    def test_bun_rank(self) -> None:
        spec = reg.ToolSpec(
            key="demo",
            name="Demo",
            kind=reg.ToolKind.BUN,
            folder="demo",
            cli_name="demo",
            description="test",
        )
        key = _install_all_sort_key(spec)
        assert key[0] == 3

    def test_plain_python_rank(self) -> None:
        spec = reg.ToolSpec(
            key="demo",
            name="Demo",
            kind=reg.ToolKind.PYTHON,
            folder="demo",
            cli_name="demo",
            description="test",
        )
        key = _install_all_sort_key(spec)
        assert key[0] == 1


class TestInstallTool:
    @pytest.mark.usefixtures("demo_project")
    def test_unknown_tool_raises_key_error(
        self,
        sample_tools_yaml,
        clified_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _setup_tools_yaml(
            clified_root, monkeypatch, sample_tools_yaml.read_text(encoding="utf-8")
        )
        reg.load_registry()
        with pytest.raises(KeyError):
            install_tool("nonexistent")

    @pytest.mark.usefixtures("demo_project")
    def test_directory_not_found_returns_false(
        self,
        clified_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        content = textwrap.dedent("""
            workspace:
              root: ".."
              name: Test

            tools:
              missing:
                kind: python
                folder: nonexistent-dir
                cli_name: missing
                description: "Missing tool"
        """)
        _setup_tools_yaml(clified_root, monkeypatch, content)
        reg.load_registry()
        result = install_tool("missing")
        assert result is False


class TestInstallAll:
    def test_no_tools_returns_false(
        self,
        clified_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        content = textwrap.dedent("""
            workspace:
              root: ".."
              name: Empty

            tools: {}
        """)
        _setup_tools_yaml(clified_root, monkeypatch, content)
        reg.load_registry()
        result = install_all()
        assert result is False

    @pytest.mark.usefixtures("demo_project")
    def test_restores_env_after_run(
        self,
        sample_tools_yaml,
        clified_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("CLIFIED_INSTALL_ALL", raising=False)
        _setup_tools_yaml(
            clified_root, monkeypatch, sample_tools_yaml.read_text(encoding="utf-8")
        )
        reg.load_registry()
        with patch("clified.installer.unified.install_tool", return_value=True):
            install_all()
        assert "CLIFIED_INSTALL_ALL" not in os.environ


class TestInstallToolActions:
    @pytest.mark.usefixtures("demo_project")
    def test_uninstall_action(
        self,
        sample_tools_yaml,
        clified_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _setup_tools_yaml(
            clified_root, monkeypatch, sample_tools_yaml.read_text(encoding="utf-8")
        )
        reg.load_registry()
        with patch("clified.installer.unified._ToolPythonInstaller") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.run_uninstall.return_value = True
            mock_cls.return_value = mock_inst
            result = install_tool("demo", action="uninstall")
        assert result is True

    def test_unknown_action_returns_false(
        self,
        clified_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        content = textwrap.dedent("""
            workspace:
              root: ".."
              name: Test

            tools:
              demo:
                name: "Demo Tool"
                kind: python
                folder: demo-tool
                cli_name: demo
                description: "Test"
        """)
        _setup_tools_yaml(clified_root, monkeypatch, content)
        (clified_root.parent / "demo-tool").mkdir(exist_ok=True)
        (clified_root.parent / "demo-tool" / "pyproject.toml").write_text(
            "[project]\nname='demo'\n", encoding="utf-8"
        )
        reg.load_registry()
        with patch("clified.installer.unified._ToolPythonInstaller") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst
            result = install_tool("demo", action="unknown_action")
        assert result is False
