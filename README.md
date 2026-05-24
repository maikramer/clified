# Clified

Instalador universal e **biblioteca CLI** para ferramentas Python, Rust e Bun.

Inclui infraestrutura reutilizável inspirada no [denv](https://github.com/) (LocatelliDockerManager): output JSON, retry, circuit breaker, diagnóstico de erros e integração MCP.

## Estrutura

```
clified/
├── install.sh / install.ps1 / install.bat
├── tools.yaml                               # registry das suas ferramentas
├── config/
│   ├── clified.yml.example                # config global opcional
│   └── install-all-constraints.txt
├── pyproject.toml
└── src/clified/
    ├── logging.py                         # Logger Rich/ANSI (instalador)
    ├── hooks.py                           # post_install (ex.: MCP)
    ├── cli/                               # ← do denv: output JSON, decorators
    │   ├── output.py
    │   └── decorators.py
    ├── core/                              # ← do denv: config, retry, state
    │   ├── config.py
    │   ├── retry.py
    │   ├── circuit_breaker.py
    │   ├── state_store.py
    │   └── exceptions.py
    ├── patterns/                          # ← do denv: diagnóstico por regex
    │   ├── base.json
    │   ├── loader.py
    │   └── services/build.json
    ├── integrations/
    │   └── mcp.py                         # registo Cursor MCP
    └── installer/
        ├── registry.py
        ├── unified.py
        └── ...
```

## Instalação

```bash
git clone https://github.com/maikramer/clified.git
cd clified
cp tools.yaml.example tools.yaml   # primeira vez
./install.sh --list
./install.sh minha-ferramenta
```

`tools.yaml` é local (não vai para o git) — registe os projectos do seu workspace.

## Desenvolvimento

```bash
pip install -e ".[dev]"
pytest -q
```


## Biblioteca para os seus CLIs

```python
from clified.cli import OutputFormatter, handle_cli_errors
from clified.core import RetryEngine, ConfigManager, get_state_store
from clified.patterns import get_pattern_loader

# Saída JSON para automação
out = OutputFormatter(json_mode=True)
out.success({"tool": "mytool"}, message="ok")

# Retry com backoff
RetryEngine().execute(risky_function)

# Diagnóstico de logs de build
diag = get_pattern_loader().get_diagnosis("ModuleNotFoundError: foo")

# Estado persistente (~/.clified/state.json)
store = get_state_store()
store.set("installs", "mytool", {"version": "1.0"})
```

## Hooks e MCP

```yaml
tools:
  denv:
    kind: python
    folder: ../GitClones/LocatelliDockerManager
    cli_name: denv
    post_install: clified.hooks:register_mcp
```

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `CLIFIED_ROOT` | Pasta clified |
| `CLIFIED_TOOLS` | Caminho alternativo para tools.yaml |
| `CLIFIED_RETRY=1` | Retry automático na instalação |
| `CLIFIED_MCP_NAME` | Nome do servidor MCP (hook) |
| `INSTALL_PREFIX` | Prefixo (~/.local) |

## Origem do código denv

Módulos adaptados do **denv** (LocatelliDockerManager), generalizados:

| Clified | Origem denv |
|---------|-------------|
| `cli/output.py` | `denv/core/output.py` |
| `cli/decorators.py` | `denv/cli/decorators.py` |
| `core/exceptions.py` | subset de `denv/core/exceptions.py` |
| `core/retry.py` | `denv/core/retry_engine.py` |
| `core/circuit_breaker.py` | `denv/core/circuit_breaker.py` |
| `core/state_store.py` | `denv/core/state_store.py` (API genérica) |
| `core/config.py` | `denv/core/config.py` (sem Docker/Swarm) |
| `patterns/` | `denv/error_patterns/` |
| `integrations/mcp.py` | `installer/installer.py` setup_mcp |

A lógica Docker/Swarm permanece no repositório denv — não foi copiada.
