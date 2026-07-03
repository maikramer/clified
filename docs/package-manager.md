# Package manager

Since **0.8.0**, Clified tracks installed tools in a local state file and
exposes subcommands for day-to-day management. This turns `--get` installs into
a lightweight package manager — without a central binary store (tools stay in
their git clones and project venvs).

## State file

**Path:** `~/.config/clified/state.json` (override: `CLIFIED_HOME`)

Managed by `StateStore` (`clified.core.state_store`). Structure:

```json
{
  "metadata": {
    "version": "1.0",
    "created_at": "2026-07-03T…",
    "updated_at": "2026-07-03T…"
  },
  "namespaces": {
    "installed": {
      "text2d": { … InstallReceipt … },
      "denv": { … }
    }
  }
}
```

Receipts live under namespace `installed`, keyed by **tool key** (lowercase).

Corrupt JSON is recreated with a warning — individual bad receipts are skipped
during `load_all()`.

## InstallReceipt

Each successful install/update writes an `InstallReceipt`:

| Field | Description |
|-------|-------------|
| `kind` | `python`, `rust`, or `bun` |
| `cli_name` | Command name in `INSTALL_PREFIX/bin` |
| `source` | `catalog`, `repo`, or `local` |
| `repo` | Git URL (catalog/repo installs) |
| `ref` | Branch/tag/SHA at install time |
| `commit` | Resolved HEAD SHA after clone |
| `tools_yaml` | Path to registry used |
| `project_root` | Tool source directory |
| `venv_path` | Python venv path (if applicable) |
| `catalog_name` | Catalog entry name (e.g. `text2d`) |
| `install_prefix` | Where wrappers were written |
| `repo_clone_path` | Path under `sources/` |
| `artifacts` | List of wrapper/binary paths |
| `installed_at` | First install timestamp (UTC ISO) |
| `updated_at` | Last modify timestamp |
| `clified_version` | Clified version that wrote the receipt |

Receipt keys use the **`tools.yaml` key** (`spec.key`), not always the display
name — important for monorepos with multiple tools.

## Subcommands

All support `--json` for scripting.

### `clified list`

Shows installed tools with health status (`ok` / `broken`):

```bash
clified list
clified list --json
```

**Broken** means the receipt exists but critical paths are missing (venv,
project root, or all artifacts).

### `clified search <query>`

Searches the **remote catalog** (not local state):

```bash
clified search game
clified search text --json
```

Matches against catalog name and description.

### `clified get <tool>[@ref]`

Fetch from catalog + install. Alias of `clified-install --get`. See
[Remote catalog](catalog.md).

```bash
clified get denv
clified get text2d@v1.2.0
clified get my-tool --repo https://github.com/user/repo.git
```

### `clified install [tool]`

Install from the **active** `tools.yaml` (requires `CLIFIED_TOOLS` or a prior
`get`):

```bash
export CLIFIED_TOOLS=/path/to/tools.yaml
clified install my-tool
clified install --all
```

Requires `tool` or `--all` — omitting both is an error (does not silently
install nothing).

### `clified update [tool] [--all]`

Updates installed tools:

```bash
clified update text2d
clified update --all
clified update text2d --ref main --force
```

Per-tool update flow (`_update_one`):

1. Load receipt; restore `CLIFIED_TOOLS` / `CLIFIED_ROOT` from receipt
2. `git pull` on `repo_clone_path` (skipped on detached HEAD / SHA pin)
3. Re-run installer with `action=update` (`UV_VENV_CLEAR=0` — keeps venv)
4. Update receipt (`commit`, `updated_at`)

Use `--ref` to move a pinned install to a new branch/tag/SHA.

### `clified uninstall <tool> [--purge]`

```bash
clified uninstall text2d
clified uninstall text2d --purge
```

1. Restore environment from receipt
2. Run installer `action=uninstall` (remove wrappers)
3. Remove receipt **only if uninstall succeeds**
4. With `--purge`: delete clone in `sources/` **unless** another active
   receipt shares the same `repo_clone_path`

### `clified catalog`

List known remote tools (same as `clified-install --catalog`).

### `clified doctor [--fix] [--tool NAME]`

Diagnostics — see [Doctor](doctor.md).

## Restoring context from a receipt

Commands like `update` and `uninstall` must re-read the original `tools.yaml`
from the clone. `_restore_env_from_receipt`:

1. Clears stale `CLIFIED_TOOLS` / `CLIFIED_ROOT`
2. Sets them from receipt fields
3. Resets and reloads the in-memory registry

This prevents cross-contamination when managing multiple installed tools in one
session.

## Source types

| `source` | How installed | Typical receipt fields |
|----------|---------------|------------------------|
| `catalog` | `clified get denv` | `catalog_name`, `repo`, `repo_clone_path` |
| `repo` | `get --repo <url>` | `repo`, `repo_clone_path` |
| `local` | `clified install` with local `CLIFIED_TOOLS` | `tools_yaml`, `project_root` |

## Legacy compatibility

These still work and write/read the same state file:

```bash
clified-install --get denv
clified-install denv          # with CLIFIED_TOOLS set
clified denv                  # delegates to unified.main
clified --get denv
```

Prefer explicit subcommands (`clified get`, `clified list`) for clarity.

## Environment variables

| Variable | Effect on package manager |
|----------|---------------------------|
| `CLIFIED_HOME` | State file and sources base directory |
| `CLIFIED_SOURCES` | Clone directory for `--get` |
| `CLIFIED_TOOLS` | Active registry for `install` |
| `CLIFIED_ROOT` | Project root after `--get` |
| `INSTALL_PREFIX` | Wrapper destination (default `~/.local`) |

## Related

- [Concepts](concepts.md) — state layer overview
- [Remote catalog](catalog.md) — `--get` and cloning
- [Doctor](doctor.md) — fix broken state
- [Install pipeline](install-pipeline.md) — what install/update runs internally
