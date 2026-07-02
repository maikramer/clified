"""Fallback do Logger quando o Rich não está disponível."""

from __future__ import annotations

import pytest

from clified import logging as clified_logging
from clified.logging import Logger


@pytest.fixture
def plain_logger(monkeypatch: pytest.MonkeyPatch) -> Logger:
    monkeypatch.setattr(clified_logging, "_RICH", False)
    return Logger()


def test_info_warn_error_step_success_emit_plain(
    plain_logger: Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    plain_logger.info("hello")
    plain_logger.warn("careful")
    plain_logger.error("boom")
    plain_logger.step("doing")
    plain_logger.success("done")
    out = capsys.readouterr().out
    assert "INFO hello" in out
    assert "WARN careful" in out
    assert "ERROR boom" in out
    assert "STEP doing" in out
    assert "OK done" in out


def test_header_panel_table_emit_plain(
    plain_logger: Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    plain_logger.header("My Section")
    plain_logger.panel("body content", title="Panel Title")
    plain_logger.table([("k1", "v1"), ("k2", "v2")], title="Table Title")
    out = capsys.readouterr().out
    assert "## My Section" in out
    assert "Panel Title" in out
    assert "body content" in out
    assert "Table Title" in out
    assert "k1: v1" in out
    assert "k2: v2" in out


def test_warning_is_alias_of_warn(
    plain_logger: Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    plain_logger.warning("aliased")
    assert "WARN aliased" in capsys.readouterr().out


def test_exception_emits_error_and_traceback(
    plain_logger: Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    """logger.exception existe (chamado por bun/rust/python/base) — emite ERROR + traceback."""
    try:
        raise ValueError("boom-detail")
    except ValueError:
        plain_logger.exception("build falhou")
    captured = capsys.readouterr()
    assert "ERROR build falhou" in captured.out
    assert "ValueError" in captured.out
    assert "boom-detail" in captured.out


def test_is_json_suppresses_human_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Em modo JSON, info/step/success/panel/table são suprimidos; warn/error vão para stderr."""
    monkeypatch.setattr(clified_logging, "_RICH", False)
    monkeypatch.setenv("CLIFIED_JSON", "1")
    log = Logger()
    assert log.is_json is True
    log.info("hidden-info")
    log.step("hidden-step")
    log.success("hidden-ok")
    log.panel("hidden-panel", title="t")
    log.table([("k", "v")], title="t")
    log.warn("visible-warn")
    log.error("visible-error")
    captured = capsys.readouterr()
    assert captured.out == ""  # stdout limpo para JSON
    assert "WARN visible-warn" in captured.err
    assert "ERROR visible-error" in captured.err


def test_is_json_off_by_default(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("CLIFIED_JSON", raising=False)
    monkeypatch.setattr(clified_logging, "_RICH", False)
    log = Logger()
    assert log.is_json is False
    log.info("shown")
    assert "INFO shown" in capsys.readouterr().out
