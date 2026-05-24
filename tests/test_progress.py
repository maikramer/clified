"""Testes StepRunner."""

from __future__ import annotations

from clified.cli.progress import Step, StepRunner


def test_step_runner_success() -> None:
    steps = [Step("a"), Step("b")]
    runner = StepRunner(steps, title="Test", quiet=True)
    calls: list[str] = []

    ok = runner.run([lambda: calls.append("a"), lambda: calls.append("b")])

    assert ok is True
    assert calls == ["a", "b"]
    summary = runner.summary()
    assert summary["title"] == "Test"
    assert len(summary["steps"]) == 2
    assert all(s["success"] for s in summary["steps"])


def test_step_runner_stops_on_error() -> None:
    steps = [Step("ok"), Step("fail")]
    runner = StepRunner(steps, quiet=True)

    def boom() -> None:
        msg = "nope"
        raise RuntimeError(msg)

    ok = runner.run([lambda: None, boom])

    assert ok is False
    assert len(runner.results) == 2
    assert runner.results[1].success is False
