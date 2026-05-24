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

Cada projecto traz o seu `install.sh`, aponta `CLIFIED_TOOLS` para o `tools.yaml` local e instala o Clified via pip na primeira execução. **Não é necessário clonar o repositório Clified.**

## Início rápido

```bash
pip install --user clified
# ou: pipx install clified

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
```

## Projectos que usam Clified

| CLI | Repositório | Tipo |
|-----|-------------|------|
| **denv** | LocatelliDockerManager | Python |
| **pc** | ProjetoCursor | Python |
| **text2d**, **materialize**, … | GameDev | Python / Rust / Bun |
| **ai2print** | ai2print | Rust + Python (hook) |

## Licença

MIT — ver [LICENSE](LICENSE).
