"""Relatórios de diagnóstico (inspirado no denv DiagnosisReporter)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from clified.patterns.loader import PatternMatch, get_pattern_loader


@dataclass
class DiagnosisReport:
    source: str
    service: str | None
    matches: list[PatternMatch]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "service": self.service,
            "matches": [m.to_dict() for m in self.matches],
            "count": len(self.matches),
        }

    def to_markdown(self) -> str:
        lines = ["# Diagnóstico", "", f"**Fonte:** `{self.source[:200]}`", ""]
        if not self.matches:
            lines.append("_Nenhum padrão encontrado._")
            return "\n".join(lines)
        for i, m in enumerate(self.matches, 1):
            lines.append(f"## {i}. {m.pattern.category} — {m.pattern.id}")
            lines.append(f"**Diagnóstico:** {m.pattern.diagnosis}")
            lines.append(f"**Match:** `{m.matched_text}`")
            if m.pattern.solutions:
                lines.append("**Soluções:**")
                for s in m.pattern.solutions:
                    lines.append(f"- {s}")
            lines.append("")
        return "\n".join(lines)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def diagnose_text(text: str, *, service: str | None = None) -> DiagnosisReport:
    loader = get_pattern_loader()
    detected = service or loader.detect_service(text)
    matches = loader.analyze_log(text, detected)
    return DiagnosisReport(source=text, service=detected, matches=matches)
