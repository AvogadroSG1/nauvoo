# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Nauvoo is a push daemon that syncs Obsidian markdown callout annotations back to Google Drive as comments/replies. It is the push counterpart to Ring Station (which pulls Drive docs into Obsidian markdown). The daemon polls a vault directory, finds callouts lacking an `id:` field (meaning they haven't been pushed yet), posts them via the Drive API, and stamps the returned ID back into the markdown.

## Commands

```bash
uv sync --extra google --extra dev          # install all dependencies
uv run pytest                               # run test suite (unit + integration)
uv run pytest tests/unit/test_callout_parser.py -v   # run one test file
uv run ruff check src/ tests/               # lint
uv run ruff check --fix src/ tests/         # lint with auto-fix
uv run nauvoo                               # run daemon (needs OBSIDIAN_DOCS_DIR set)
```

Tests split into `tests/unit/` (no network, no real filesystem beyond `tmp_path`) and `tests/integration/` (needs real Google credentials). CI runs unit tests only.

## Architecture

Hexagonal (ports and adapters). The dependency rule is strict:

- `src/nauvoo/domain/` — pure parsing logic, no I/O, no external imports. `callout_parser.py` detects unpushed `[!reply]`/`[!new-comment]` callouts; `callout_stamper.py` inserts returned Drive IDs into callout headers (idempotent — skips lines already containing `id:`).
- `src/nauvoo/ports/` — abstract base classes. `driven/` (DriveWriterPort, VaultReaderPort) are things the app calls out to; `driving/` (VaultWatcherPort) drives the app.
- `src/nauvoo/adapters/` — concrete port implementations. Adapters never import from other adapters; domain never imports from adapters.
- `src/nauvoo/application/coordinator.py` — `VaultSyncCoordinator`, the orchestration loop.
- `src/nauvoo/daemon.py` — the composition root. All wiring (env vars, OAuth, adapter construction) happens here and only here. Google-client imports are deferred to inside functions so the `google` extra stays optional.

### The sync loop

`PollingWatcherAdapter` snapshots mtimes of all `.md` files on an interval and calls `VaultSyncCoordinator.sync_files` with changed paths. For each file the coordinator: reads content → extracts `doc-id:` from YAML frontmatter (files without one are skipped) → `parse_unpushed()` → posts each callout via `DriveWriterPort` (replies go to `parent_comment_id`, which the parser tracks from the enclosing `[!comment] id:...` header) → `stamp_id()` rewrites the callout header with the new ID → writes the file back. Per-file errors are logged and swallowed so one bad file doesn't kill the loop.

### Callout protocol

A callout **with** `id:` has already been pushed; **without** `id:` it's pending. Replies are nested blockquotes (`> > [!reply]`), new top-level comments are single blockquotes (`> [!new-comment]`). Line numbers from the parser are 0-indexed and are what the stamper uses to find the header line.

## Conventions

- **TDD**: write the failing test first, verify it fails, implement minimally, run the full suite, commit.
- Google adapter unit tests use the `__new__` bypass to avoid importing `googleapiclient`:
  ```python
  adapter = GoogleDriveWriterAdapter.__new__(GoogleDriveWriterAdapter)
  adapter._drive = MagicMock()
  ```
- `from __future__ import annotations` at the top of every module; type annotations on all public methods; no bare `except:`.
- Ruff enforces style (line length 88, E501 ignored; rules E, W, F, I, UP, B, SIM). Run it before every commit.
- Commit format: Conventional Commits prefixes (`feat`, `fix`, `test`, `docs`, `refactor`, `chore`), and every commit includes both co-authors:
  ```
  Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
  Co-Authored-By: Claude <noreply@anthropic.com>
  ```
- Keep PRs under 300 lines, one logical change per PR.
- Design/implementation plans live in `docs/plans/` as dated markdown files.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OBSIDIAN_DOCS_DIR` | _(required)_ | Directory of Ring Station markdown files |
| `GOOGLE_CLIENT_SECRETS` | `~/Keys/client_secrets.json` | OAuth client secrets (shared with Ring Station) |
| `GOOGLE_TOKEN_FILE` | `~/.config/nauvoo/token.json` | OAuth token (deliberately separate from Ring Station's — see `docs/plans/2026-03-07-separate-oauth-tokens-design.md`) |
| `NAUVOO_POLL_INTERVAL` | `30` | Polling interval in seconds |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

Nauvoo needs the full `drive` scope (read+write). `GoogleAuthAdapter._check_scopes()` fails fast with an actionable error if the stored token lacks required scopes.
