# Contributing to Nauvoo

## Development Setup

```bash
# Install all dependencies
uv sync --extra google --extra dev

# Run the test suite
uv run pytest

# Run linter
uv run ruff check src/ tests/

# Run a specific test file
uv run pytest tests/unit/test_callout_parser.py -v
```

Tests are organized into `unit/` (no network, no filesystem) and `integration/` (needs real credentials). CI runs unit tests only.

## Architecture Overview

Nauvoo uses hexagonal architecture -- domain core at the center, ports as interfaces, adapters as plug-ins.

```
domain/       Pure parsing logic. No I/O. No external imports.
ports/        Abstract base classes. Contracts between layers.
adapters/     Concrete implementations of ports.
application/  Orchestration (VaultSyncCoordinator).
```

The rule: domain code never imports from adapters. Adapters never import from other adapters. All wiring happens in `daemon.py` -- the composition root.

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `CalloutParser` | `domain/callout_parser.py` | Detect unpushed `[!reply]` / `[!new-comment]` callouts |
| `CalloutStamper` | `domain/callout_stamper.py` | Stamp returned Drive IDs back into callout headers |
| `VaultSyncCoordinator` | `application/coordinator.py` | Orchestrate parse, push, and stamp per file |
| `FilesystemVaultAdapter` | `adapters/driven/filesystem_vault.py` | Read/write markdown files |
| `PollingWatcherAdapter` | `adapters/driving/polling_watcher.py` | Poll vault directory for changed files |
| `GoogleDriveWriterAdapter` | `adapters/driven/google_drive_writer.py` | Post replies/comments via Drive API |

## Callout Protocol

Ring Station writes callouts with `id:` fields (already pushed). Nauvoo watches for callouts **without** `id:` fields -- those are unpushed.

**Unpushed reply** (user wrote this):

```markdown
> > [!reply] · me · 2026-03-07
> > My reply text
```

**After Nauvoo pushes** (stamped with Drive ID):

```markdown
> > [!reply] id:reply789 · me · 2026-03-07
> > My reply text
```

**New top-level comment**:

```markdown
> [!new-comment] · me · 2026-03-07
> My question
```

## Test-Driven Development

All changes follow TDD:

1. Write the failing test
2. Run it -- verify it fails with the expected error
3. Write minimal implementation to make it pass
4. Run the full suite -- verify nothing regressed
5. Commit

**Unit test rules:**

- No network calls, no filesystem access (use `tmp_path` fixture for filesystem tests)
- Mock all external dependencies via `unittest.mock`

**Google adapter tests** use the `__new__` bypass pattern to avoid importing `googleapiclient`:

```python
adapter = GoogleDriveWriterAdapter.__new__(GoogleDriveWriterAdapter)
adapter._drive = MagicMock()
```

## Code Style

Ruff enforces formatting and linting. Run before every commit:

```bash
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/   # auto-fix safe issues
```

Key conventions:

- `from __future__ import annotations` at the top of every module
- Type annotations on all public methods
- No bare `except:` -- always catch a specific exception type

## Commit Format

Every commit must include both co-authors:

```
feat: add callout parser

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>
```

Use Conventional Commits prefixes: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`.

Keep PRs under 300 lines. One logical change per PR.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OBSIDIAN_DOCS_DIR` | _(required)_ | Path to Ring Station markdown files |
| `GOOGLE_CLIENT_SECRETS` | `~/Keys/client_secrets.json` | OAuth client secrets |
| `GOOGLE_TOKEN_FILE` | `~/ObsidianNotes/.../token.json` | OAuth token |
| `NAUVOO_POLL_INTERVAL` | `30` | Polling interval in seconds |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Running the Daemon Locally

```bash
# Start the daemon (foreground, logs to stdout)
OBSIDIAN_DOCS_DIR=~/ObsidianNotes/Work/16-Google-Docs \
uv run nauvoo
```
