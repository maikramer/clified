# Changelog

## 0.9.0 — 2026-07

Breaking alignment with the **AiGameKit** monorepo rename (was GameDev).

- **Catalog keys**: `gamedev` → `aigamekit`, `gamedevlab` → `aigamekitlab`.
  Use `clified get aigamekit` (install-all) instead of `clified get gamedev`.
- **repos**: all public catalog entries now clone
  `https://github.com/maikramer/AiGameKit.git`.
- **Examples / docs**: `tools.aigamekit.yaml.example`,
  `aigamekit-constraints.txt.example`, and hooks docs reference
  `aigamekit_shared` / `aigamekit-lab` / `aigamekit-install`.

## 0.8.4 — 2026-07

Code-review sweep + lint-debt cleanup. All ~65 pre-existing Ruff findings fixed,
strict `ruff check`/`ruff format --check` re-enabled as hard gates in `ci.yml`
and `publish.yml`, and regression tests added for the main fixes.

Bug fixes (full code review of `installer/`, `core/`, `cli`, `hooks`):

- **Retry masked permanent failures as success**: `_run_with_retry` returned
  `result.success` even when the installer returned `False`, so a failed install
  could be recorded as a valid receipt. Now `result.success and bool(result.result)`.
- **Retry retried non-transient errors**: `FileNotFoundError`/`PermissionError` are
  now non-retryable; retry jitter is capped by `max_delay` (could previously exceed
  it after jitter was applied).
- **`install_all` keyed by `spec.key`** (not `spec.name`) — prevents receipt
  collisions for tools sharing a display name.
- **Single-`get` receipt key** resolved to the canonical tool key, consistent with
  `install`/`update`.
- **`UV_VENV_CLEAR` leaked** into the environment after `update`; now saved/restored.
- **`tools.yaml` parse errors** (`ValueError`) now carry the offending tool key and
  are caught at the CLI top level (clean message, no traceback) in both `cli.py`
  and `unified.py`.
- **`InstallReceipt.from_dict`** with a corrupt non-list `artifacts` (string/int)
  no longer char-splits or raises; falls back to `[]`.
- **Windows venv site-packages**: `_find_site_packages` now also recognizes the
  `Lib/site-packages` layout. `pyproject.toml` relative-dep patching preserves
  original line endings (uses `open(newline="")`).
- **`venv` ABI bounds** (`max_python`) verified after both uv and non-uv venv
  creation.
- **PyTorch CUDA detection** logs the failure instead of a silent CPU fallback.
- **Bun installer**: `assert`-based flow control replaced with explicit None
  checks; Windows `.cmd` wrappers invoked via `cmd /c`.
- **`base` (Windows PATH)**: `winreg.OpenKey` moved inside the `try` so
  `CloseKey` always runs.
- **`clified --version`** works in the new subcommand dispatcher (early return).
- **`clified install` with no tool and no `--all`** now errors explicitly instead
  of installing nothing silently.
- **`uninstall`** no longer removes the receipt when the uninstall action reports
  failure; `--purge` preserves a clone shared by other active receipts.
- **`doctor --fix`** is safer: `_orphan_wrappers` only touches files carrying the
  `gerado por clified` marker (won't delete user scripts); interactive
  confirmation prompt when a tty is present; JSON output records the actions
  taken; `--tool` filter is case/`-`/`_`-insensitive.
- **Git error classification**: generic `"not found"` removed from auth markers;
  a regex now matches `repository '…' not found` precisely, so a missing branch
  is no longer reported as "Acesso negado".
- **Catalog**: `_rm_tree`/`_current_branch` promoted to public `rm_tree`/
  `current_branch`; relative-dep helper uses `Path.chmod` + `contextlib.suppress`.
- **JSON error paths**: `cli`/`unified` error reporting routed through
  `output.error(...)` so `--json` emits structured errors instead of plain logs.

Regression tests: retry (B1/B5/B13), Windows site-packages (A1), corrupt
`artifacts` (B8), `--version` and `install` no-operand (C1/C12), `doctor`
orphan-marker + filter normalization (C3/C9), branch-not-found not auth (B12).

## 0.8.3 — 2026-07

Release-process fix: unblock the PyPI publish workflow.

- The `Publish PyPI` and `CI` GitHub Actions gated on `ruff check src tests` /
  `ruff format --check`, which fail with ~65 pre-existing lint findings (mostly
  in tests: `S603`/`S607` for `subprocess.run(["git", …])`, missing annotations,
  etc.). The publish job exited at the lint step, so **0.8.0/0.8.1/0.8.2 never
  reached PyPI** (stuck at 0.7.4). Lint and format checks are now advisory
  (`continue-on-error: true`); `pytest`, the coverage threshold, and the smoke
  CLI remain hard gates. Lint debt to be cleaned up in a follow-up.

## 0.8.2 — 2026-07

Bug fixes found by removing legacy installs and reinstalling all tools via the
0.8 package manager (real catalog tools: AiGameKit + Locatelli).

- **uv + relative `file:` deps**: `_rewrite_relative_file_deps` produced a
  malformed `file://C:\\...` URL (2 slashes + backslashes) that uv rejects —
  blocking every AiGameKit Python tool that depends on `aigamekit-shared @
  file:../Shared`. Now emits a proper `file:///C:/.../Shared` (3 slashes,
  forward slashes); pip still tolerates it.
- **`Logger.exception`**: missing method — `bun_installer`, `rust_installer`,
  `python_installer`, `base`, and the `pytorch` hook all call
  `logger.exception(...)` on failure, so any build/install error crashed with
  `AttributeError` and masked the real cause. Added `Logger.exception` (delegates
  to `error` + active traceback).
- **SHA pinning on a shallow clone**: `clified get tool@<short-sha>` on an
  existing shallow clone failed with `pathspec ... did not match`. `git fetch
  --depth 1 origin <short-sha>` is rejected (server treats the short SHA as a
  ref name) and the `git fetch origin` fallback respects the shallow boundary
  (doesn't bring old SHAs). `_checkout_ref` now falls back to `git fetch
  --unshallow origin` so the SHA is present for checkout.
- Tests: +2 regression tests (`Logger.exception`, SHA-unshallow on shallow
  clone); updated `test_rewrite_relative_file_dep` for the corrected file URL.

## 0.8.1 — 2026-07

Bug fixes found via end-to-end testing of the 0.8.0 package-manager features.

- **`clified list`** (human table): fix crash (`ValueError: too many values to
  unpack`) — now uses a proper multi-column table.
- **`clified search`**: show `(privado)` / `[instalado]` markers in human output
  (Rich markup escaped so `[instalado]` is no longer swallowed).
- **`InstallReceipt`**: add `repo_clone_path` field and propagate it from
  `ReceiptContext` so `update` / `uninstall --purge` can locate the clone.
- **`clified update`**: record the fresh post-pull commit in the receipt (was
  overwritten with the stale pre-update commit).
- **Windows cleanup**: `shutil.rmtree(ignore_errors=True)` silently failed on
  read-only git object files — replaced with a robust `_rm_tree` (chmod + retry)
  used by `uninstall --purge` and re-clones over stale sources.
- **Pinning by commit SHA**: `git fetch --depth 1 origin <sha>` fails on repos
  without `allowReachableSHA1InWant` (local/bare) — fall back to a full fetch +
  `git checkout <sha>`.
- **Detached-HEAD recovery**: a clone left detached (from a previous SHA pin)
  broke plain `clified get`/`update` (`git pull` on detached HEAD) — now returns
  to the default branch before pulling (`_current_branch` / `_default_branch`).
- **`doctor`**: fix `NameError` (`Path` import); `--fix` now also removes orphan
  wrappers (previously only warned).
- **`--json` clean output**: suppress Rich panels/STEP/INFO and redirect pip /
  venv subprocess stdout to stderr so `get`/`install`/`update`/`uninstall` emit
  pure JSON on stdout (`CLIFIED_JSON` env, `Logger.is_json`).
- **Legacy `clified <unknown-tool>`**: return a clean error (exit 1) instead of
  an uncaught `KeyError` traceback; `--json` emits a structured error.
- Tests: +8 regression tests (receipt `repo_clone_path`, branch helpers, robust
  `rmtree`, SHA-fetch fallback, `Logger.is_json`, unknown-tool clean error).

## 0.8.0 — 2026-07

Package manager features: installed-tool state, subcommands, pinning.

- **State file** (`~/.config/clified/state.json`): receipts per installed tool
  (repo, ref, commit, venv, artifacts, timestamps).
- **Subcommands on `clified`**: `list`, `update`, `uninstall`, `search`, `get`,
  `install`, `doctor`, `catalog` — `clified-install` unchanged (back-compat).
- **`clified list`**: installed tools with ok/broken status (distinct from
  `clified-install --list` which lists tools.yaml registry).
- **`clified update [tool|--all]`**: git pull / ref checkout + reinstall deps.
- **`clified uninstall <tool> [--purge]`**: uninstall via receipt; `--purge`
  removes clone in `sources/`.
- **Pinning**: `clified get tool@ref` / `--get tool@ref` (branch, tag, or commit SHA).
- **`clified search <term>`**: filter remote catalog; marks private/installed.
- **`--json`** on install/update/uninstall/get (machine-readable results).
- **`doctor`**: broken receipts, orphan wrappers; `--fix` cleans stale state.
- Bun uninstall removes `node_modules`.

## 0.7.4 — 2026-07

Bundled catalog snapshot: AiGameKit monorepo tools.

- `bundled/registry.yaml`: add 16 public entries for `maikramer/AiGameKit`
  (`text2d`, `text3d`, `materialize`, `vibegame`, meta `aigamekit` → `all`, …).
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
