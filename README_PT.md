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
| **Catálogo** | `maikramer/clified-catalog` (live) + bundled fallback | Mapeia um nome curto (`denv`) → repo + ferramenta, para `--get` |

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

## Catálogo remoto (`--get` / `--catalog`)

O catálogo mapeia um nome curto (`denv`, `cissapi`, `pc`, …) a um repo + ferramenta.
Por defeito é lido live de [`maikramer/clified-catalog`](https://github.com/maikramer/clified-catalog)
(raw `registry.yaml`) com cache local (`~/.config/clified/catalog.cache.yaml`,
TTL 1h) e fallback ao snapshot embutido quando offline. **Adicionar uma
ferramenta não exige novo release do Clified** — basta editar o repo do catálogo.

```bash
clified-install --catalog                    # listar ferramentas remotas (privadas marcadas)
clified-install --refresh-catalog --catalog  # ignora cache, força refresh
clified-install --get denv                   # buscar + instalar do catálogo
```

| Env | Default | Efeito |
|-----|---------|--------|
| `CLIFIED_CATALOG` | *(unset)* | Override do catálogo: URL (`http(s)://`) ou path local. |
| `CLIFIED_CATALOG_TTL` | `3600` | TTL da cache em segundos. `0` = sempre fetch; `-1` = só bundled (offline). |

### Público vs privado

Cada entrada tem um campo opcional `access: public|private` (default `public`).
O `--catalog` marca as privadas como `(privado)` e o `--get <privada>` avisa
antes de clonar. Repos privados (ex.: `LocatelliSupermercados/*`) são clonados
com as tuas creds git (chave SSH / token HTTPS via git credential manager). Sem
acesso, o Clified **falha de forma suave** com mensagem clara — sem crash do git.

### Publicar uma ferramenta

- **Sem catálogo** — qualquer repo público: `clified-install --get minha-tool --repo https://github.com/.../x.git`.
- **Catálogo público** — abre um PR a `maikramer/clified-catalog` com
  `access: public`.
- **Self-host** — mantém o teu `registry.yaml` (repo privado ou ficheiro local)
  e aponta o Clified com `CLIFIED_CATALOG=<url-ou-path>`.

### A partir de um projecto clonado

```bash
git clone https://github.com/seu-usuario/meu-cli.git
cd meu-cli
./install.sh
meu-cli --help
```

## Documentação

Índice completo: **[docs/README.md](docs/README.md)** (inglês)

| Guia | Conteúdo |
|------|----------|
| [Getting started](docs/getting-started.md) | Instalação, fluxo numa máquina virgem, `install.sh` |
| [Concepts](docs/concepts.md) | **Motor, registo, catálogo, state** — como encaixa tudo |
| [Architecture](docs/architecture.md) | Diagrama, resolução de paths, tipos de installer |
| [Install pipeline](docs/install-pipeline.md) | CLI → installer → wrappers → receipt (detalhe) |
| [Remote catalog](docs/catalog.md) | `registry.yaml`, cache, `--get`, pinning de versão |
| [Package manager](docs/package-manager.md) | `state.json`, receipts, list/update/uninstall |
| [Doctor](docs/doctor.md) | Diagnósticos, `--fix`, wrappers órfãos |
| [Referência `tools.yaml`](docs/tools-yaml.md) | Campos, tipos Python/Rust/Bun, exemplos |
| [Hooks](docs/hooks.md) | `post_install`, hooks built-in, hooks locais |
| [Migrating a project](docs/migrating-a-project.md) | denv / pc / AiGameKit / ai2print |
| [CLI library](docs/library.md) | OutputFormatter, retry, patterns, Click |
| [Troubleshooting](docs/troubleshooting.md) | PEP 668, Python errado no PATH, MCP |
| [Development](docs/development.md) | Testes, release PyPI, contribuir |

## Gerir ferramentas instaladas (`clified` 0.8+)

Depois de instalar com `--get` ou a partir de um clone, o Clified regista cada
ferramenta em `~/.config/clified/state.json`. Usa o entry point **`clified`**
(não `clified-install`) para gestão do dia-a-dia:

```bash
clified list                         # instaladas (ok / broken)
clified list --json
clified search game                  # procurar no catálogo remoto
clified get text2d                   # buscar + instalar do catálogo
clified get text2d@v1.2.0            # pin branch/tag/commit
clified update text2d                # git pull + refrescar deps
clified update --all                 # actualizar tudo o que está instalado
clified uninstall text2d --purge     # remover ferramenta + clone em sources/
clified doctor --fix                 # receipts broken + wrappers órfãos
```

`clified-install` e invocações legadas (`clified text2d`, `clified --get denv`)
continuam totalmente suportadas.

## Comandos principais

```bash
clified-install --list              # ferramentas no tools.yaml activo
clified-install denv                # instalar uma ferramenta
clified-install denv --action reinstall --force
clified-install all                 # todas (respeita install_order)
clified-install --catalog           # listar ferramentas remotas conhecidas
clified-install --refresh-catalog --catalog  # forçar refresh do catálogo
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
| **text2d**, **materialize**, … | AiGameKit | Python / Rust / Bun |
| **ai2print** | ai2print | Rust + Python (hook) |

## Licença

MIT — ver [LICENSE](LICENSE).
