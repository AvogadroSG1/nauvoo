# Nauvoo

Push daemon for syncing Obsidian markdown callouts back to Google Drive comments.

## Overview

Nauvoo is the push counterpart to [Ring Station](https://github.com/AvogadroSg1/ring-station). Ring Station pulls Google Drive documents into Obsidian markdown. Nauvoo watches those markdown files and pushes any callout annotations you write back to Google Drive as comments and replies.

## How It Works

Ring Station writes markdown files like:

```markdown
> [!comment] id:abc123 · Alice · 2026-03-07
> Can you clarify section 2?
>
> > [!reply] id:reply456 · Alice · 2026-03-07
> > Sure, I'll update it.
```

When you add a reply or new comment without an `id:` field, Nauvoo detects it and pushes it:

```markdown
> > [!reply] · me · 2026-03-07
> > Looks good to me.
```

After pushing, Nauvoo stamps the returned ID back into the file:

```markdown
> > [!reply] id:reply789 · me · 2026-03-07
> > Looks good to me.
```

New top-level comments use `[!new-comment]`:

```markdown
> [!new-comment] · me · 2026-03-07
> I had a question about the approach here.
```

## Architecture

Hexagonal architecture — domain core at center, ports as interfaces, adapters as plugins.

```
domain/       Pure parsing logic. No I/O.
ports/        Abstract base classes (VaultReaderPort, DriveWriterPort, VaultWatcherPort).
adapters/     Concrete implementations.
application/  VaultSyncCoordinator — orchestrates the push loop.
```

## Setup

```bash
# Install dependencies
uv sync --extra google --extra dev

# Run daemon
OBSIDIAN_DOCS_DIR=~/ObsidianNotes/Work/16-Google-Docs \
GOOGLE_CLIENT_SECRETS=~/Keys/client_secrets.json \
uv run nauvoo
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OBSIDIAN_DOCS_DIR` | _(required)_ | Directory of Ring Station markdown files |
| `GOOGLE_CLIENT_SECRETS` | `~/Keys/client_secrets.json` | OAuth client secrets |
| `GOOGLE_TOKEN_FILE` | `~/.config/nauvoo/token.json` | OAuth token |
| `NAUVOO_POLL_INTERVAL` | `30` | Polling interval in seconds |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
