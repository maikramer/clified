"""Motor de retry com backoff exponencial."""

from __future__ import annotations

import functools
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Type

from clified.logging import Logger

from .exceptions import ConnectionError, RetryableError, TimeoutError


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.25
    retryable_exceptions: tuple[Type[Exception], ...] = field(
        default_factory=lambda: (RetryableError, ConnectionError, TimeoutError, OSError)
    )
    non_retryable_exceptions: tuple[Type[Exception], ...] = field(
        default_factory=lambda: (KeyboardInterrupt, SystemExit, ValueError)
    )

    def with_attempts(self, max_attempts: int) -> RetryPolicy:
        return RetryPolicy(
            max_attempts=max_attempts,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            exponential_base=self.exponential_base,
            jitter=self.jitter,
            jitter_factor=self.jitter_factor,
            retryable_exceptions=self.retryable_exceptions,
            non_retryable_exceptions=self.non_retryable_exceptions,
        )


@dataclass
class RetryAttempt:
    attempt_number: int
    started_at: datetime
    ended_at: datetime | None = None
    success: bool = False
    exception: Exception | None = None
    delay_before: float = 0.0


@dataclass
class RetryResult:
    success: bool
    result: Any = None
    attempts: list[RetryAttempt] = field(default_factory=list)
    total_duration: float = 0.0
    final_exception: Exception | None = None


    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def was_retried(self) -> bool:
        return len(self.attempts) > 1


class RetryEngine:
    AGGRESSIVE = RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=30.0)
    CONSERVATIVE = RetryPolicy(max_attempts=3, base_delay=5.0, max_delay=120.0)
    QUICK = RetryPolicy(max_attempts=2, base_delay=0.5, max_delay=5.0)

    def __init__(
        self,
        policy: RetryPolicy | None = None,
        logger: Logger | None = None,
        on_retry: Callable[[int, Exception | None, float], None] | None = None,
    ) -> None:
        self.policy = policy or RetryPolicy()
        self.logger = logger or Logger()
        self.on_retry = on_retry

    def calculate_delay(self, attempt: int) -> float:
        delay = self.policy.base_delay * (self.policy.exponential_base ** (attempt - 1))
        delay = min(delay, self.policy.max_delay)
        if self.policy.jitter:
            jitter_range = delay * self.policy.jitter_factor
            delay = max(0.1, delay + random.uniform(-jitter_range, jitter_range))
        return delay

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        if attempt >= self.policy.max_attempts:
            return False
        if isinstance(exception, self.policy.non_retryable_exceptions):
            return False
        if isinstance(exception, self.policy.retryable_exceptions):
            return True
        return False

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> RetryResult:
        attempts: list[RetryAttempt] = []
        start = time.time()
        final_exception: Exception | None = None

        for attempt_num in range(1, self.policy.max_attempts + 1):
            attempt = RetryAttempt(attempt_number=attempt_num, started_at=datetime.now())
            if attempt_num > 1:
                delay = self.calculate_delay(attempt_num)
                attempt.delay_before = delay
                self.logger.info(f"Retry {attempt_num}/{self.policy.max_attempts} em {delay:.1f}s...")
                if self.on_retry:
                    self.on_retry(attempt_num, final_exception, delay)
                time.sleep(delay)

            try:
                result = func(*args, **kwargs)
                attempt.success = True
                attempt.ended_at = datetime.now()
                attempts.append(attempt)
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_duration=time.time() - start,
                )
            except Exception as exc:
                attempt.success = False
                attempt.exception = exc
                attempt.ended_at = datetime.now()
                attempts.append(attempt)
                final_exception = exc
                self.logger.warn(
                    f"Tentativa {attempt_num}/{self.policy.max_attempts} falhou: {str(exc)[:120]}"
                )
                if not self.should_retry(exc, attempt_num):
                    break

        return RetryResult(
            success=False,
            attempts=attempts,
            total_duration=time.time() - start,
            final_exception=final_exception,
        )


def with_retry(policy: RetryPolicy | None = None, logger: Logger | None = None):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            engine = RetryEngine(policy=policy, logger=logger)
            result = engine.execute(func, *args, **kwargs)
            if result.success:
                return result.result
            if result.final_exception:
                raise result.final_exception
            raise RuntimeError("Retry failed without exception")

        return wrapper

    return decorator
