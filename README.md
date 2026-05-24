# Clified

Instalador universal e **biblioteca CLI** para ferramentas Python, Rust e Bun.

Infraestrutura reutilizável consolidada a partir de **denv** (LocatelliDockerManager), **pc** (ProjetoCursor) e **GameDev** — sem hardcodar ferramentas no código.

## Estrutura

```
clified/
├── install.sh / install.ps1 / install.bat
├── tools.yaml                               # registry local (gitignored)
├── tools.yaml.example
├── examples/                                # migração GameDev / denv / pc
├── config/
│   ├── clified.yml.example
│   ├── install-all-constraints.txt
│   └── gamedev-constraints.txt.example
└── src/clified/
    ├── logging.py
    ├── cli/                                 # output JSON, Click scaffold, StepRunner
    ├── core/                                # config, retry, paths, state
    ├── patterns/                            # diagnóstico regex + reporter
    ├── hooks/                               # MCP, skills, pip check, nvdiffrast
    ├── integrations/mcp.py
    └── installer/
```

## Instalação

### PyPI (recomendado)

```bash
pip install --user clified
# ou: pipx install clified

clified-install --list
clified-install minha-ferramenta
```

Cada repositório de ferramenta traz o seu `tools.yaml` e define `CLIFIED_TOOLS` no `install.sh` — **não é necessário clonar o Clified**.

### Desenvolvimento do Clified

```bash
git clone https://github.com/maikramer/clified.git
cd clified
pip install -e ".[dev]"
cp tools.yaml.example tools.yaml   # registry local opcional
./install.sh --list
```

Para CLIs Click: `pip install -e ".[cli]"` (grupo `--json` / `--quiet` / `--verbose`).

### Publicar no PyPI

```bash
pip install hatch
hatch build
hatch publish   # requer credenciais PyPI / token
```

Ou crie um **GitHub Release** — o workflow `.github/workflows/publish.yml` publica automaticamente (Trusted Publishing).

## Migração de workspaces existentes

| Origem | Exemplo YAML | O que fica no repo original |
|--------|--------------|----------------------------|
| **GameDev** | `examples/tools.gamedev.yaml.example` | `*_extras.py`, constraints ML, lógica PyTorch |
| **denv** | `examples/tools.denv.yaml.example` | Docker/Swarm, FastMCP server |
| **pc** | `examples/tools.pc.yaml.example` | comandos Flutter/deploy, skill do projecto |

Campos novos em `tools.yaml`:

| Campo | Uso |
|-------|-----|
| `custom_install` | Hook `modulo:func(installer)` substituindo `pip install -e` |
| `install_before_mode: venv_only` | Equivalente ao `--text2d-venv-only` do GameDev |
| `install_order` | Ordem em `clified-install all` |
| `post_install` | MCP, skills Cursor, `pip check`, etc. |

Hooks prontos (`clified.hooks`):

- `register_mcp` / `register_mcp_serve` — Cursor MCP
- `register_cursor_skill` — skill do pc/GameDev
- `pip_check` — validação pós-install
- `install_nvdiffrast` — extra PyTorch (GameDev)

## Desenvolvimento

```bash
pip install -e ".[dev]"
pytest -q
```

## Biblioteca para os seus CLIs

```python
from clified.cli import OutputFormatter, handle_cli_errors
from clified.cli.app import create_cli_group  # pip install clified[cli]
from clified.cli.progress import StepRunner, Step
from clified.core import find_project_root, RetryEngine, get_state_store
from clified.patterns import diagnose_text

out = OutputFormatter(json_mode=True)
out.success({"tool": "mytool"})

report = diagnose_text(log_text)
print(report.to_markdown())
```

## Hooks e MCP

```yaml
tools:
  denv:
    kind: python
    folder: ../LocatelliDockerManager
    cli_name: denv
    post_install: clified.hooks:register_mcp_serve
```

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `CLIFIED_TOOLS` | Caminho para `tools.yaml` do projecto (**principal**) |
| `CLIFIED_HOME` | Config do utilizador (default `~/.config/clified`) |
| `CLIFIED_ROOT` | Checkout local do Clified (só dev) |
| `CLIFIED_MIN_VERSION` | Versão mínima no `pip install` automático (default `0.4.0`) |
| `CLIFIED_RETRY=1` | Retry automático na instalação |
| `CLIFIED_MCP_NAME` | Nome do servidor MCP (hook) |
| `CLIFIED_PROJECT_ROOT` | Override para `find_project_root()` |
| `INSTALL_PREFIX` | Prefixo (~/.local) |

## Origem do código

| Clified | Origem |
|---------|--------|
| `cli/output.py`, `cli/decorators.py` | denv |
| `cli/app.py`, `cli/progress.py` | denv + pc (`DeployUI` / StepRunner) |
| `core/paths.py` | pc |
| `hooks/skills.py` | GameDev `skill_install.py` |
| `hooks/mcp.py`, `hooks/pytorch.py` | denv + GameDev |
| `patterns/reporter.py` | denv `DiagnosisReporter` |
| `installer/registry.py` (campos extras) | GameDev unified installer |

A lógica Docker/Swarm permanece no denv; pipelines ML específicos permanecem no GameDev — registados via YAML, não hardcoded.
