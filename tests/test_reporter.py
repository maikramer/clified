"""Testes DiagnosisReporter."""

from __future__ import annotations

from clified.patterns.reporter import diagnose_text


def test_diagnose_text_module_not_found() -> None:
    report = diagnose_text("ModuleNotFoundError: No module named 'foo'")
    assert report.service is not None
    assert isinstance(report.to_dict()["matches"], list)
    md = report.to_markdown()
    assert "Diagnóstico" in md
