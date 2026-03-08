#!/usr/bin/env bash
set -euo pipefail

export OBSIDIAN_DOCS_DIR="$HOME/ObsidianNotes/Work/16-Google-Docs"
export GOOGLE_CLIENT_SECRETS="$HOME/Keys/client_secrets.json"
export GOOGLE_TOKEN_FILE="$HOME/.config/nauvoo/token.json"
export NAUVOO_POLL_INTERVAL=30
export LOG_LEVEL=INFO

cd /Users/poconnor/nauvoo
exec /opt/homebrew/bin/uv run nauvoo
