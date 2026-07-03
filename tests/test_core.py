"""Testes core: retry, state, config, circuit breaker."""

from __future__ import annotations

import pytest

from clified.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
)
from clified.core.config import ClifiedConfig, ConfigManager
from clified.core.exceptions import RetryableError
from clified.core.retry import RetryEngine, RetryPolicy
from clified.core.state_store import StateStore


def test_retry_succeeds_after_transient_failure() -> None:
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            msg = "temp"
            raise RetryableError(msg)
        return "ok"

    result = RetryEngine(policy=RetryPolicy(max_attempts=3, base_delay=0.01)).execute(
        flaky
    )
    assert result.success
    assert result.result == "ok"
    assert result.attempt_count == 2


def test_state_store_namespace(tmp_path) -> None:
    store = StateStore(path=tmp_path / "state.json")
    store.set("installs", "demo", {"v": "1"})
    assert store.get("installs", "demo") == {"v": "1"}
    assert store.delete("installs", "demo")
    assert store.get("installs", "demo") is None


def test_config_manager_defaults(tmp_path) -> None:
    cfg_path = tmp_path / "clified.yml"
    mgr = ConfigManager(config_file=cfg_path)
    cfg = mgr.get_config()
    assert isinstance(cfg, ClifiedConfig)
    assert cfg.retry.max_attempts == 3


def test_circuit_breaker_opens_after_failures() -> None:
    config = CircuitBreakerConfig(
        failure_threshold=2,
        success_threshold=1,
        recovery_timeout=60,
        half_open_max_calls=1,
    )
    cb = CircuitBreaker("test", config=config)

    def fail() -> None:
        msg = "boom"
        raise RuntimeError(msg)

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(fail)

    with pytest.raises(CircuitOpenError):
        cb.call(lambda: None)


def test_retry_does_not_mask_false_return_as_success() -> None:
    """B1: um installer que devolve ``False`` (falha permanente) não deve ser
    reportado como sucesso pelo retry — senão gravaria receipt de install falhada."""
    from unittest.mock import patch

    from clified.installer.unified import _run_with_retry
    from clified.logging import Logger

    def fails() -> bool:
        return False

    assert _run_with_retry("install", fails, Logger(), max_attempts=1) is False
    with patch("clified.core.retry.time.sleep"):
        assert _run_with_retry("install", fails, Logger(), max_attempts=3) is False


def test_retry_does_not_retry_file_not_found() -> None:
    """B5: ``FileNotFoundError`` é permanente — não deve haver retry."""
    calls = {"n": 0}

    def boom() -> str:
        calls["n"] += 1
        raise FileNotFoundError("nope")

    result = RetryEngine(policy=RetryPolicy(max_attempts=3, base_delay=0.01)).execute(
        boom
    )
    assert result.success is False
    assert calls["n"] == 1


def test_retry_delay_respects_max_after_jitter() -> None:
    """B13: o jitter não deve fazer o delay exceder ``max_delay``."""
    engine = RetryEngine(
        policy=RetryPolicy(
            max_attempts=5, base_delay=100.0, max_delay=10.0, jitter=True
        )
    )
    for attempt in range(1, 6):
        assert engine.calculate_delay(attempt) <= 10.0
