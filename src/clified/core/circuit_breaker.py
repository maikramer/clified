"""Circuit breaker genérico."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from typing_extensions import Self

from clified.logging import Logger

from .exceptions import CircuitBreakerError

if TYPE_CHECKING:
    from collections.abc import Callable


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(CircuitBreakerError):
    def __init__(self, circuit_name: str, time_until_retry: float) -> None:
        self.circuit_name = circuit_name
        self.time_until_retry = time_until_retry
        super().__init__(
            f"Circuit '{circuit_name}' aberto. Tente novamente em {time_until_retry:.0f}s",
        )


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    success_threshold: int = 3
    recovery_timeout: int = 60
    half_open_max_calls: int = 3
    failure_window: int = 300
    excluded_exceptions: tuple = field(
        default_factory=lambda: (KeyboardInterrupt, SystemExit)
    )


@dataclass
class CircuitStats:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    blocked_calls: int = 0
    state_changes: int = 0


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        logger: Logger | None = None,
    ) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.logger = logger or Logger()
        self._state = CircuitState.CLOSED
        self._lock = threading.RLock()
        self._failures: deque = deque()
        self._successes_in_half_open = 0
        self._calls_in_half_open = 0
        self._opened_at: datetime | None = None
        self._stats = CircuitStats()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN and self._should_attempt_recovery():
                self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    def _should_attempt_recovery(self) -> bool:
        if self._opened_at is None:
            return False
        return (
            datetime.now(tz=UTC) - self._opened_at
        ).total_seconds() >= self.config.recovery_timeout

    def _transition_to(self, new_state: CircuitState) -> None:
        if self._state == new_state:
            return
        old = self._state
        self._state = new_state
        self._stats.state_changes += 1
        if new_state == CircuitState.HALF_OPEN:
            self._successes_in_half_open = 0
            self._calls_in_half_open = 0
        elif new_state == CircuitState.OPEN:
            self._opened_at = datetime.now(tz=UTC)
        elif new_state == CircuitState.CLOSED:
            self._failures.clear()
            self._opened_at = None
        self.logger.info(f"Circuit '{self.name}': {old.value} -> {new_state.value}")

    def record_success(self) -> None:
        with self._lock:
            self._stats.total_calls += 1
            self._stats.successful_calls += 1
            if self._state == CircuitState.HALF_OPEN:
                self._successes_in_half_open += 1
                if self._successes_in_half_open >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def record_failure(self, exception: Exception | None = None) -> None:
        with self._lock:
            if exception and isinstance(exception, self.config.excluded_exceptions):
                return
            self._stats.total_calls += 1
            self._stats.failed_calls += 1
            self._failures.append(datetime.now(tz=UTC))
            if self._state == CircuitState.HALF_OPEN or (
                self._state == CircuitState.CLOSED
                and self._count_recent_failures() >= self.config.failure_threshold
            ):
                self._transition_to(CircuitState.OPEN)

    def _count_recent_failures(self) -> int:
        cutoff = datetime.now(tz=UTC) - timedelta(seconds=self.config.failure_window)
        while self._failures and self._failures[0] < cutoff:
            self._failures.popleft()
        return len(self._failures)

    def allow_request(self) -> bool:
        with self._lock:
            current = self.state
            if current == CircuitState.CLOSED:
                return True
            if current == CircuitState.OPEN:
                self._stats.blocked_calls += 1
                return False
            if self._calls_in_half_open < self.config.half_open_max_calls:
                self._calls_in_half_open += 1
                return True
            self._stats.blocked_calls += 1
            return False

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if not self.allow_request():
            remaining = float(self.config.recovery_timeout)
            if self._opened_at:
                elapsed = (datetime.now(tz=UTC) - self._opened_at).total_seconds()
                remaining = max(0.0, self.config.recovery_timeout - elapsed)
            raise CircuitOpenError(self.name, remaining)
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            raise


class CircuitBreakerRegistry:
    _instance: CircuitBreakerRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> Self:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._circuits: dict[str, CircuitBreaker] = {}
                    cls._instance = inst
        return cls._instance  # type: ignore[return-value]

    def get_or_create(
        self, name: str, config: CircuitBreakerConfig | None = None
    ) -> CircuitBreaker:
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name=name, config=config)
        return self._circuits[name]


circuit_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str, config: CircuitBreakerConfig | None = None
) -> CircuitBreaker:
    return circuit_registry.get_or_create(name, config)
