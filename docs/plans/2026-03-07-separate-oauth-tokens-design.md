# Separate OAuth Tokens for Nauvoo and Ring Station

**Date**: 2026-03-07
**Status**: Accepted

## Problem

Nauvoo and Ring Station both default their `DEFAULT_TOKEN_FILE` to the same path:

```
~/ObsidianNotes/Work/02-Technical/Code/GoogleDataExtraction/credentials/token.json
```

Each project requests different Google OAuth scopes:

| Project | Scopes |
|---------|--------|
| Nauvoo | `drive` (read+write) |
| Ring Station | `calendar.readonly`, `documents.readonly`, `gmail.readonly`, `drive.readonly` |

Whichever project authenticates last overwrites the token, breaking the other project's required scopes.

## Decision

Give each project its own token file using XDG-style paths:

- **Nauvoo**: `~/.config/nauvoo/token.json`
- **Ring Station**: `~/.config/ring-station/token.json`

The `GOOGLE_TOKEN_FILE` env var override continues to work in both projects. The shared `client_secrets.json` at `~/Keys/client_secrets.json` remains unchanged — it's the OAuth app identity, not user-specific token state.

## Alternatives Considered

1. **Named tokens under `~/Keys/`** — Rejected. Mixes ephemeral OAuth tokens with static client secrets.
2. **Shared auth library** — Rejected. Over-engineering for two projects with ~10 lines of auth code each.

## Changes

### Nauvoo

1. `daemon.py` — Change `DEFAULT_TOKEN_FILE` to `~/.config/nauvoo/token.json`
2. `google_auth.py` — Add `_check_scopes()` method (matches Ring Station's implementation). Raises `ValueError` with actionable message if token is missing required scopes.
3. `README.md`, `CONTRIBUTING.md` — Update default token path in env var tables.

### Ring Station

1. `daemon.py` — Change `DEFAULT_TOKEN_FILE` to `~/.config/ring-station/token.json`
2. `README.md`, `CONTRIBUTING.md`, `CLAUDE.md` — Update default token path in env var tables.

## Migration

1. Delete the old shared token at `~/ObsidianNotes/Work/02-Technical/Code/GoogleDataExtraction/credentials/token.json`
2. Run each project — each triggers OAuth re-auth and writes its token to the new XDG path
3. No data loss risk — tokens are ephemeral and auto-regenerated
