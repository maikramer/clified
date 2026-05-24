"""Carregador de padrões de erro (regex JSON)."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ErrorPattern:
    id: str
    pattern: str
    category: str
    priority: int
    diagnosis: str
    solutions: list[str]
    service: str = ""
    related_errors: list[str] = field(default_factory=list)
    docs_url: str | None = None
    _compiled: re.Pattern[str] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._compiled is None:
            try:
                self._compiled = re.compile(self.pattern, re.IGNORECASE)
            except re.error:
                self._compiled = re.compile(r"(?!)")

    def matches(self, text: str) -> bool:
        return bool(self._compiled and self._compiled.search(text))

    def find_match(self, text: str) -> re.Match[str] | None:
        return self._compiled.search(text) if self._compiled else None


@dataclass
class PatternMatch:
    pattern: ErrorPattern
    matched_text: str
    start: int
    end: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern.id,
            "service": self.pattern.service,
            "category": self.pattern.category,
            "diagnosis": self.pattern.diagnosis,
            "solutions": self.pattern.solutions,
            "matched_text": self.matched_text,
            "priority": self.pattern.priority,
            "related_errors": self.pattern.related_errors,
            "docs_url": self.pattern.docs_url,
        }


@dataclass
class ServiceInfo:
    name: str
    version: str
    aliases: list[str]
    description: str
    pattern_count: int


class ErrorPatternLoader:
    """Carrega padrões de ``patterns/`` (base + services/*.json)."""

    DEFAULT_KEYWORDS: dict[str, list[str]] = {
        "build": ["pip", "cargo", "npm", "compile", "install", "module not found", "rustc"],
        "python": ["python", "pip", "venv", "pyproject", "ModuleNotFoundError"],
        "rust": ["cargo", "rustc", "rustup", "compiling"],
    }

    def __init__(
        self,
        patterns_dir: Path | None = None,
        service_keywords: dict[str, list[str]] | None = None,
    ) -> None:
        self.patterns_dir = Path(patterns_dir or Path(__file__).resolve().parent)
        self.services_dir = self.patterns_dir / "services"
        self.service_keywords = service_keywords or dict(self.DEFAULT_KEYWORDS)
        self._cache: dict[str, list[ErrorPattern]] = {}
        self._service_info: dict[str, ServiceInfo] = {}
        self._all_patterns: list[ErrorPattern] | None = None
        self._lock = threading.RLock()
        self._load_base()

    def _load_base(self) -> None:
        base = self.patterns_dir / "base.json"
        if base.is_file():
            self._cache["base"] = self._load_file(base)

    def _load_file(self, path: Path) -> list[ErrorPattern]:
        patterns: list[ErrorPattern] = []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            service = data.get("service", "unknown")
            for p in data.get("patterns", []):
                patterns.append(
                    ErrorPattern(
                        id=p.get("id", ""),
                        pattern=p.get("pattern", ""),
                        category=p.get("category", "unknown"),
                        priority=int(p.get("priority", 3)),
                        diagnosis=p.get("diagnosis", ""),
                        solutions=list(p.get("solutions") or []),
                        service=service,
                        related_errors=list(p.get("related_errors") or []),
                        docs_url=p.get("docs_url"),
                    )
                )
            info = ServiceInfo(
                name=service,
                version=data.get("version", "1.0"),
                aliases=list(data.get("aliases") or []),
                description=data.get("description", ""),
                pattern_count=len(patterns),
            )
            self._service_info[service] = info
            for alias in info.aliases:
                self._service_info[alias.lower()] = info
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass
        return patterns

    def _ensure_service(self, service: str) -> None:
        key = service.lower()
        if key in self._cache:
            return
        with self._lock:
            if key in self._cache:
                return
            path = self.services_dir / f"{key}.json"
            self._cache[key] = self._load_file(path) if path.is_file() else []

    def get_patterns_for_service(self, service: str) -> list[ErrorPattern]:
        key = service.lower()
        if key in self._service_info:
            key = self._service_info[key].name.lower()
        self._ensure_service(key)
        patterns = list(self._cache.get(key, []))
        patterns.extend(self._cache.get("base", []))
        return sorted(patterns, key=lambda p: p.priority)

    def detect_service(self, log_line: str) -> str | None:
        log_lower = log_line.lower()
        scores: dict[str, int] = {}
        for service, keywords in self.service_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in log_lower)
            if score:
                scores[service] = score
        if not scores:
            return None
        return max(scores.items(), key=lambda x: x[1])[0]

    def analyze_log(self, log: str, service: str | None = None) -> list[PatternMatch]:
        if service is None:
            service = self.detect_service(log)
        patterns = self.get_patterns_for_service(service) if service else self.get_all_patterns()
        matches: list[PatternMatch] = []
        for pattern in patterns:
            match = pattern.find_match(log)
            if match:
                matches.append(
                    PatternMatch(
                        pattern=pattern,
                        matched_text=match.group(0),
                        start=match.start(),
                        end=match.end(),
                    )
                )
        seen: set[str] = set()
        unique: list[PatternMatch] = []
        for m in sorted(matches, key=lambda x: x.pattern.priority):
            key = f"{m.pattern.category}:{m.pattern.id}"
            if key not in seen:
                seen.add(key)
                unique.append(m)
        return unique

    def get_diagnosis(self, log: str, service: str | None = None) -> dict[str, Any] | None:
        matches = self.analyze_log(log, service)
        return matches[0].to_dict() if matches else None

    def get_all_patterns(self) -> list[ErrorPattern]:
        if self._all_patterns is not None:
            return self._all_patterns
        with self._lock:
            if self.services_dir.is_dir():
                for path in self.services_dir.glob("*.json"):
                    self._ensure_service(path.stem)
            seen: set[str] = set()
            all_p: list[ErrorPattern] = []
            for patterns in self._cache.values():
                for p in patterns:
                    if p.id not in seen:
                        seen.add(p.id)
                        all_p.append(p)
            self._all_patterns = sorted(all_p, key=lambda p: p.priority)
            return self._all_patterns

    def list_services(self) -> list[ServiceInfo]:
        if self.services_dir.is_dir():
            for path in self.services_dir.glob("*.json"):
                self._ensure_service(path.stem)
        seen: set[str] = set()
        out: list[ServiceInfo] = []
        for info in self._service_info.values():
            if info.name not in seen:
                seen.add(info.name)
                out.append(info)
        return sorted(out, key=lambda s: s.name)

    def reload(self) -> None:
        with self._lock:
            self._cache.clear()
            self._service_info.clear()
            self._all_patterns = None
            self._load_base()


_loader: ErrorPatternLoader | None = None
_loader_lock = threading.Lock()


def get_pattern_loader(patterns_dir: Path | None = None) -> ErrorPatternLoader:
    global _loader
    if _loader is None:
        with _loader_lock:
            if _loader is None:
                _loader = ErrorPatternLoader(patterns_dir)
    return _loader
