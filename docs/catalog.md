# Remote catalog

The catalog maps a **short name** (`denv`, `text2d`, `pc`) to a git repository
and a tool key inside that repository's `tools.yaml`. It powers:

```bash
clified get denv
clified-install --get denv
curl -fsSL .../install.sh | bash -s -- --get denv
clified search game
clified catalog
```

Adding a tool to the catalog **does not require a new Clified release** — edit
the live catalog repository and users pick it up on the next fetch (subject to
cache TTL).

## Data model

### `registry.yaml` entry

```yaml
tools:
  denv:
    repo: https://github.com/LocatelliSupermercados/denv.git
    tool: denv                    # key in the repo's tools.yaml
    tools_yaml: tools.yaml        # optional; default tools.yaml
    description: "Docker env manager"
    access: private               # public (default) | private (informational)
```

Parsed into `RepoSpec`:

| Field | Meaning |
|-------|---------|
| `name` | Catalog key (e.g. `denv`) |
| `repo` | Git clone URL |
| `tool` | Tool key passed to the installer (`all` installs every tool) |
| `tools_yaml` | Path to registry inside the clone |
| `ref` | Branch, tag, or commit SHA (from `tool@ref` syntax) |
| `access` | `public` or `private` — affects warnings, not git behaviour |

### Three sources of catalog data

Resolution order in `load_catalog()`:

```
1. CLIFIED_CATALOG (URL or local path)     ← override
2. Remote fetch (default GitHub raw URL)   ← live catalog
   └── cache: ~/.config/clified/catalog.cache.yaml (TTL)
3. Bundled snapshot (wheel)                 ← offline fallback
   └── src/clified/bundled/registry.yaml
```

| Env | Default | Effect |
|-----|---------|--------|
| `CLIFIED_CATALOG` | *(unset)* | URL (`https://…`) or local file path |
| `CLIFIED_CATALOG_TTL` | `3600` | Cache TTL in seconds |
| | `0` | Always fetch remote (ignore cache age) |
| | `-1` | Bundled only — never fetch (offline mode) |

Refresh explicitly:

```bash
clified catalog --refresh-catalog
clified-install --refresh-catalog --catalog
```

## Cache behaviour

When TTL > 0:

1. If `catalog.cache.yaml` exists and is younger than TTL → use cache
2. Else fetch remote URL; on success, write cache
3. On fetch failure → fall back to stale cache, then bundled snapshot

`--refresh-catalog` busts CDN caching on `raw.githubusercontent.com` by
appending `?v=<timestamp>` to the fetch URL.

## The `--get` / `clified get` flow

```
User: clified get text2d@v1.2.0
         │
         ▼
  parse_tool_at_ref → ("text2d", "v1.2.0")
         │
         ▼
  load_catalog() → RepoSpec for "text2d" with ref=v1.2.0
         │
         ▼
  clone_or_update(spec) → ~/.config/clified/sources/text2d
         │
         ├── new clone: git clone [--depth 1] + checkout ref
         └── existing:  git fetch/pull or checkout SHA
         │
         ▼
  resolve_tools_yaml(spec, dest) → path to tools.yaml
         │
         ▼
  Set CLIFIED_TOOLS, CLIFIED_ROOT on os.environ
  reset_registry(); load_registry()
         │
         ▼
  install_tool(spec.tool) or install_all() if tool=="all"
         │
         ▼
  record_install(receipt_key, InstallReceipt(...))
```

### Clone directory

Default: `~/.config/clified/sources/<catalog_name>/`

Override: `CLIFIED_SOURCES` or `--sources-dir`.

Each catalog entry gets one directory. Re-running `get` updates the same clone.

### Version pinning (`tool@ref`)

Syntax: `clified get text2d@v1.2.0`, `clified get text2d@abc1234`

| Ref type | Behaviour |
|----------|-----------|
| Branch / tag | Shallow fetch + pull or checkout |
| Commit SHA (7–40 hex) | Checkout exact commit; detached HEAD |
| Omitted | Default branch (HEAD) |

**Update note:** `clified update text2d` runs `git pull` on the clone. For
SHA-pinned installs (detached HEAD), pull is skipped — use
`clified update text2d --ref <new-ref>` to move to a new pin.

### Installing all tools from a repo

If the catalog entry has `tool: all`:

```yaml
  gamedev:
    repo: https://github.com/maikramer/GameDev.git
    tool: all
```

`clified get gamedev` runs `install_all`, respecting `install_order` and
`install_before` in the repo's `tools.yaml`.

## Git error messages

Clone failures are classified before reaching the user:

| Git stderr pattern | User message |
|--------------------|--------------|
| Auth failure markers | "Acesso negado ou repositório inacessível" + hint about SSH/token |
| `repository '<url>' not found` | Same (private or missing repo) |
| Other | Raw stderr appended to "git clone falhou" |

A **missing branch** (`pathspec did not match`) is **not** treated as auth
failure — you get the raw git error instead.

Private repos (`access: private`) show a warning before clone; access still
depends entirely on the user's git credentials.

## Without the catalog

Any public repo works with an explicit URL:

```bash
clified get my-tool --repo https://github.com/user/repo.git
clified-install --get my-tool --repo https://github.com/user/repo.git
```

The tool name must exist in that repo's `tools.yaml`. No catalog entry required.

## Self-hosting

1. Maintain your own `registry.yaml` (private git repo or local file)
2. Point users at it:

```bash
export CLIFIED_CATALOG=https://your-org.example/catalog/registry.yaml
# or
export CLIFIED_CATALOG=/path/to/registry.yaml
```

3. Optionally set `CLIFIED_CATALOG_TTL=-1` for air-gapped installs using only
   a copied file

## Publishing to the public catalog

Open a PR to [`maikramer/clified-catalog`](https://github.com/maikramer/clified-catalog)
with:

```yaml
  my-tool:
    repo: https://github.com/you/my-tool.git
    tool: my-tool
    description: "One-line description"
    access: public
```

The bundled `registry.yaml` in the Clified wheel is an **offline snapshot**
only — the live catalog is authoritative.

## Related

- [Concepts](concepts.md) — catalog vs registry vs state
- [Package manager](package-manager.md) — receipts after `get`
- [Install pipeline](install-pipeline.md) — what happens after clone
