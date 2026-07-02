# Clified

Instalador universal e biblioteca CLI para ferramentas **Python**, **Rust** e **Bun**.

Publicado no [PyPI](https://pypi.org/project/clified/) · [GitHub](https://github.com/maikramer/clified)

**English:** [README.md](README.md)

## O que é

O Clified separa duas responsabilidades:

| Peça | Onde vive | Função |
|------|-----------|--------|
| **Motor** | Pacote `clified` (PyPI) | venvs, wrappers, build Rust/Bun, hooks |
| **Registo** | `tools.yaml` em cada repo | O que instalar, onde está o código, pós-passos |
| **Catálogo** | `bundled/registry.yaml` | Mapeia um nome curto (`denv`) → repo + ferramenta, para `--get` |

Cada projecto traz o seu `install.sh`, aponta `CLIFIED_TOOLS` para o `tools.yaml` local e instala o Clified via pip na primeira execução. **Não é necessário clonar o repositório Clified.** Para ferramentas conhecidas, podes saltar até o clone do projecto — `clified-install --get <ferramenta>` clona o repo a partir do catálogo e instala a ferramenta num só passo.

## Início rápido

### One-liner (sem clonar)

Instala o motor e uma ferramenta conhecida do catálogo num só comando:

```bash
# Linux / macOS — motor + ferramenta do catálogo
curl -fsSL https://raw.githubusercontent.com/maikramer/clified/main/install.sh | bash -s -- --get denv
# Linux / macOS — só o motor, depois listar ferramentas remotas
curl -fsSL https://raw.githubusercontent.com/maikramer/clified/main/install.sh | bash
# Windows (PowerShell)
irm https://raw.githubusercontent.com/maikramer/clified/main/install.ps1 | iex
# Windows + argumentos
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/maikramer/clified/main/install.ps1))) --get denv
```

Sem argumentos, o one-liner instala o motor e mostra os próximos passos.
Lista as ferramentas conhecidas com `clified-install --catalog`, ou aponta `--get`
a qualquer repo com `--repo`:

```bash
clified-install --get minha-tool --repo https://github.com/seu-usuario/seu-cli.git
```

### A partir de um projecto clonado

```bash
git clone https://github.com/seu-usuario/meu-cli.git
cd meu-cli
./install.sh
meu-cli --help
```

## Documentação

A documentação completa está em **inglês** em [`docs/`](docs/):

| Guia | Conteúdo |
|------|----------|
| [Getting started](docs/getting-started.md) | Instalação, fluxo numa máquina virgem, `install.sh` |
| [Architecture](docs/architecture.md) | Motor, YAML, venvs e wrappers |
| [Referência `tools.yaml`](docs/tools-yaml.md) | Campos, tipos Python/Rust/Bun, exemplos |
| [Hooks](docs/hooks.md) | `post_install`, hooks built-in, hooks locais |
| [Migrating a project](docs/migrating-a-project.md) | denv / pc / GameDev / ai2print |
| [CLI library](docs/library.md) | OutputFormatter, retry, patterns, Click |
| [Troubleshooting](docs/troubleshooting.md) | PEP 668, Python errado no PATH, MCP |
| [Development](docs/development.md) | Testes, release PyPI, contribuir |

## Comandos principais

```bash
clified-install --list              # ferramentas no tools.yaml activo
clified-install denv                # instalar uma ferramenta
clified-install denv --action reinstall --force
clified-install all                 # todas (respeita install_order)
clified-install --catalog           # listar ferramentas remotas conhecidas
clified-install --get denv          # buscar + instalar ferramenta remota (catálogo)
clified-install --get minha-tool --repo https://github.com/seu-usuario/seu-cli.git
clified-install denv --retry 3      # retentar falhas transitórias até 3 tentativas
```

## Projectos que usam Clified

| CLI | Repositório | Tipo |
|-----|-------------|------|
| **denv** | LocatelliDockerManager | Python |
| **cissapi** | LocatelliCissApi | Python |
| **pc** | ProjetoCursor | Python |
| **text2d**, **materialize**, … | GameDev | Python / Rust / Bun |
| **ai2print** | ai2print | Rust + Python (hook) |

## Licença

MIT — ver [LICENSE](LICENSE).
