"""UI de etapas para operações longas (inspirado no DeployUI do pc CLI)."""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from clified.logging import Logger

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


@dataclass
class Step:
    name: str
    description: str = ""


@dataclass
class StepResult:
    name: str
    success: bool
    duration: float
    message: str = ""


class StepRunner:
    """Executa etapas nomeadas com logging Rich/ANSI."""

    def __init__(
        self,
        steps: list[Step],
        *,
        title: str = "Instalação",
        logger: Logger | None = None,
        quiet: bool = False,
    ) -> None:
        self.steps = steps
        self.title = title
        self.logger = logger or Logger()
        self.quiet = quiet
        self.results: list[StepResult] = []
        self._start = time.time()

    @contextmanager
    def step(self, index: int) -> Iterator[None]:
        if index < 0 or index >= len(self.steps):
            msg = f"Step index {index} fora do intervalo"
            raise IndexError(msg)
        spec = self.steps[index]
        if not self.quiet:
            self.logger.step(f"[{index + 1}/{len(self.steps)}] {spec.name}")
            if spec.description:
                self.logger.info(spec.description)
        t0 = time.time()
        success = True
        message = ""
        try:
            yield
        except Exception as exc:
            success = False
            message = str(exc)
            raise
        finally:
            duration = time.time() - t0
            self.results.append(
                StepResult(
                    name=spec.name, success=success, duration=duration, message=message
                ),
            )
            if success and not self.quiet:
                self.logger.success(f"{spec.name} ({duration:.1f}s)")

    def run(self, actions: list[Callable[[], Any]]) -> bool:
        if len(actions) != len(self.steps):
            msg = "Número de acções deve igualar número de etapas"
            raise ValueError(msg)
        if not self.quiet:
            self.logger.header(self.title)
        ok = True
        for i, action in enumerate(actions):
            try:
                with self.step(i):
                    action()
            except Exception:
                ok = False
                break
        return ok

    def summary(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "total_seconds": time.time() - self._start,
            "steps": [
                {
                    "name": r.name,
                    "success": r.success,
                    "duration": round(r.duration, 2),
                    "message": r.message,
                }
                for r in self.results
            ],
        }
