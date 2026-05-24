"""Diagnóstico de logs via padrões regex."""

from .loader import (
    ErrorPattern,
    ErrorPatternLoader,
    PatternMatch,
    ServiceInfo,
    get_pattern_loader,
)
from .reporter import DiagnosisReport, diagnose_text

__all__ = [
    "DiagnosisReport",
    "ErrorPattern",
    "ErrorPatternLoader",
    "PatternMatch",
    "ServiceInfo",
    "diagnose_text",
    "get_pattern_loader",
]
