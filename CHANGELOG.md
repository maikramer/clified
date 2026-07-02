# Changelog

## 0.7.4 — 2026-07

Bundled catalog snapshot: GameDev monorepo tools.

- `bundled/registry.yaml`: add 16 public entries for `maikramer/GameDev`
  (`text2d`, `text3d`, `materialize`, `vibegame`, meta `gamedev` → `all`, …).
- Keeps offline `--catalog` / `--get` usable when the remote catalog is unreachable.

## 0.7.3 — 2026-07

PATH handling for fresh machines (`pip install --user`).

- Shared bootstrap (`scripts/_bootstrap.ps1` / `_bootstrap.sh`): prepend user Scripts/bin
  to **session** PATH (normalized comparison; Windows includes `sysconfig` nt_user
  path for Anaconda/AppData layouts).
- After a successful engine install, **persist** user Scripts to the User PATH
  (Windows registry) or `~/.profile` (Unix marker `# clified: pip --user scripts on PATH`).
- `install.ps1` / `install.sh` one-liners fetch `_bootstrap` from GitHub when piped
  (`irm | iex` / `curl | bash`) so PATH fix applies on fresh machines without a clone.
- `install-bootstrap.{ps1,sh}` and `bootstrap.py`: prepend user script dirs before
  invoking `clified-install`; fix early-return when package is installed but not on PATH.

## 0.7.2 — 2026-07

Patch: make `--refresh-catalog` reliably fresh.

- `_fetch_text` now sends `Cache-Control: no-cache` / `Pragma: no-cache` and,
  on refresh (`--refresh-catalog` / `CLIFIED_CATALOG_TTL=0`), appends a
  cache-busting `?v=<ts>` query so the raw.githubusercontent.com CDN doesn't
  serve a stale catalog snapshot right after a catalog edit. The local TTL
  cache remains the clified caching layer.

## 0.7.1 — 2026-07

External catalog + graceful private-repo handling. New tools can now be added
without a Clified engine release.

### Live catalog (external repo)
- `clified-install` now reads the catalog from
  `maikramer/clified-catalog` (raw `registry.yaml`) **by default**, with a local
  cache (`~/.config/clified/catalog.cache.yaml`, TTL 1h) and fallback to the
  bundled `registry.yaml` when offline.
- `CLIFIED_CATALOG` overrides the source (URL `http(s)://` or local path).
- `CLIFIED_CATALOG_TTL`: cache TTL in seconds. `0` = always fetch; `-1` =
  bundled only (offline).
- `clified-install --refresh-catalog`: force a fresh fetch (ignores cache).
- `bundled/registry.yaml` is now an offline snapshot (commented as such).

### Public + private tools, graceful failure
- New optional `access: public|private` field per catalog entry (default
  `public`). `--catalog` marks private tools as `(privado)`; `--get <private>`
  warns before cloning.
- Private repos (e.g. `LocatelliSupermercados/*`) still clone with the user's
  git credentials. On auth/access denial (`authentication failed`,
  `permission denied`, `not found`, …) the clone now **fails gracefully** with a
  clear message instead of the raw `git` stderr.

### Publishing tools (3 paths)
- No catalog: `clified-install --get <name> --repo <url>`.
- Public catalog: open a PR to `maikramer/clified-catalog` (`access: public`).
- Self-host: point `CLIFIED_CATALOG` at your own private/local `registry.yaml`.

## 0.7.0 — 2026-07

Major overhaul: frictionless one-liner install, remote tool catalog, bootstrap
consolidation, and code-quality fixes across the installers.

### Install / one-liner
- `curl -fsSL .../install.sh | bash` and `irm .../install.ps1 | iex` now install
  the Clified engine and **delegate** the remaining args to `clified-install`
  (pipe-safe, dev-mode aware).
- `clified-install --get <tool>`: fetch + install a remote tool from the catalog
  (`bundled/registry.yaml`) in one step. `--repo <url>` overrides the source.
- `clified-install --catalog`: list remote tools known to the catalog.
- `install.bat` is now a thin wrapper around `install.ps1`.

### Bootstrap consolidation (Phase 2)
- Merged `python_select.py` into `installer/bootstrap.py` (single Python picker).
- Shared shell libraries `scripts/_bootstrap.sh` and `scripts/_bootstrap.ps1`;
  `install-bootstrap.{sh,ps1}` are now thin wrappers that source them.

### Code-quality (Phase 3)
- Single-source version: `__version__` in `clified/__init__.py` drives the
  hatchling build (`dynamic = ["version"]`); `paths.version()` reads it.
- Removed `src/clified/bundled/` ↔ root `config/`+`examples/` duplication; the
  wheel ships bundled resources from a single location.
- Consolidated CLI wrapper generation (`write_cli_wrapper`) across Python/Bun
  installers; fixed double-CR in Windows `.cmd` wrappers; standardized on
  `#!/usr/bin/env bash`.
- Shared `prepend_path_env` helper used by `check_path` and `bootstrap.run`.
- Logger no-Rich fallback now emits plain text instead of silently swallowing.
- Renamed `ConnectionError`/`TimeoutError` → `ClifiedConnectionError`/
  `ClifiedTimeoutError` (no longer shadow builtins).
- Moved `--text2d-venv-only` into `tools.yaml` as `install_before_mode: venv_only`.
- New `--retry N` CLI flag (default follows `CLIFIED_RETRY`; 1 = no retry).
- `main()` auto non-interactive when stdin isn't a TTY (pipe installs) and
  forces UTF-8 for child processes on Windows.
- Clarified docstrings of `clified.paths` vs `clified.core.paths`.

### Tests / CI (Phase 4)
- Unix-only tests skip on Windows (`skipif sys.platform == "win32"`).
- CI matrix now runs on `ubuntu-latest` **and** `windows-latest`; smoke step
  exercises `--catalog`.

## 0.6.1
- Internal installer refinements.
