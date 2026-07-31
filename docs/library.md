# CLI library

Beyond the installer, Clified exposes reusable modules — consolidated from **denv**, **pc**, and **AiGameKit**.

## Installation

```bash
pip install clified           # core + installer
pip install "clified[cli]"    # + Click scaffold
pip install "clified[dev]"    # + pytest, ruff
```

## Formatted output

```python
from clified.cli.output import OutputFormatter

out = OutputFormatter(json_mode=False, quiet=False)
out.info("Processing…")
out.success("Done")
out.error("Failed")
out.table([("Host", "localhost"), ("Port", "5432")], title="Config")
```

JSON mode for scripts and CI:

```python
out = OutputFormatter(json_mode=True)
out.success({"status": "ok", "count": 42})
```

## CLI decorators

```python
from clified.cli import handle_cli_errors

@handle_cli_errors
def main() -> None:
    ...
```

Catches known exceptions (`ClifiedError` and subclasses) and formats consistent output.

## Multi-step progress

```python
from clified.cli.progress import Step, StepRunner

runner = StepRunner()
runner.run([
    Step("Build", lambda: build()),
    Step("Deploy", lambda: deploy()),
])
```

## Click scaffold (optional)

```python
from clified.cli.app import create_cli_group

cli = create_cli_group(name="my-cli")
# Requires clified[cli] — exposes --json, --quiet, --verbose
```

## Paths and configuration

```python
from clified.core.paths import find_project_root, resolve_project_file
from clified.core.config import load_config

root = find_project_root()  # walk up until markers found
path = resolve_project_file("config/app.yml", start=root)
```

`CLIFIED_PROJECT_ROOT` overrides discovery.

## Retry and resilience

```python
from clified.core.retry import RetryEngine, RetryPolicy

engine = RetryEngine(policy=RetryPolicy(max_attempts=3, base_delay=2.0))
result = engine.execute(lambda: flaky_operation())
```

Enable retry on install: `CLIFIED_RETRY=1 clified-install …`

## State store

```python
from clified.core.state_store import get_state_store

store = get_state_store()
store.set("my_namespace", "last_deploy", {"env": "prod"})
```

JSON persistence at `~/.config/clified/state.json` (via `CLIFIED_HOME`).
Installed tools are tracked under the `installed` namespace by the installer
— see [Package manager](package-manager.md) and `clified list`.

## Error diagnosis (patterns)

```python
from clified.patterns import diagnose_text, get_pattern_loader

report = diagnose_text(log_output)
print(report.to_markdown())

loader = get_pattern_loader()
hint = loader.get_diagnosis("ModuleNotFoundError: No module named 'foo'")
```

JSON patterns in `clified/patterns/services/` — regex + suggestions (denv DiagnosisReporter style).

## Rich logging

```python
from clified.logging import Logger

log = Logger()
log.step("Building…")
log.success("Done")
```

Used internally by the installer; available for local hooks.

## Circuit breaker

```python
from clified.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

cb = CircuitBreaker("api", CircuitBreakerConfig(failure_threshold=5))
result = cb.call(lambda: api.request())
```

## MCP integration

```python
from clified.integrations.mcp import register_mcp_server

register_mcp_server("my-server", "/path/to/bin", ["mcp", "serve"])
```

Usually invoked via `clified.hooks:register_mcp_serve`.

## Module origins

| Clified module | Approximate origin |
|----------------|-------------------|
| `cli/output.py`, `cli/decorators.py` | denv |
| `cli/app.py`, `cli/progress.py` | denv + pc |
| `core/paths.py` | pc |
| `hooks/skills.py` | AiGameKit |
| `hooks/mcp.py`, `hooks/pytorch.py` | denv + AiGameKit |
| `patterns/reporter.py` | denv |

Domain logic (Docker, ML, Flutter) **stays in projects** — only CLI/install infrastructure lives in Clified.
