"""Nauvoo daemon entry point.

Usage:
    python -m nauvoo.daemon
    # or via script entry point:
    nauvoo

Environment variables:
    OBSIDIAN_DOCS_DIR: Path to Obsidian vault directory containing Ring Station docs (REQUIRED)
    GOOGLE_CLIENT_SECRETS: Path to OAuth client_secrets.json (default: ~/Keys/client_secrets.json)
    GOOGLE_TOKEN_FILE: Path to OAuth token.json (default: ~/.config/nauvoo/token.json)
    NAUVOO_POLL_INTERVAL: Poll interval in seconds (default: 30)
    LOG_LEVEL: Logging verbosity (default: INFO)
"""

from __future__ import annotations

import logging
import os
import signal
import sys
from pathlib import Path

logger = logging.getLogger("nauvoo.daemon")

DEFAULT_CLIENT_SECRETS = Path.home() / "Keys" / "client_secrets.json"
DEFAULT_TOKEN_FILE = Path.home() / ".config" / "nauvoo" / "token.json"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive",  # read + write for comments/replies
]


def main() -> None:
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    obsidian_docs_dir_str = os.environ.get("OBSIDIAN_DOCS_DIR", "")
    if not obsidian_docs_dir_str:
        logger.error("OBSIDIAN_DOCS_DIR is not set — cannot start")
        sys.exit(1)

    obsidian_docs_dir = Path(obsidian_docs_dir_str)
    poll_interval = float(os.environ.get("NAUVOO_POLL_INTERVAL", "30"))

    client_secrets = Path(
        os.environ.get("GOOGLE_CLIENT_SECRETS", str(DEFAULT_CLIENT_SECRETS))
    )
    token_file = Path(os.environ.get("GOOGLE_TOKEN_FILE", str(DEFAULT_TOKEN_FILE)))

    logger.info("Nauvoo daemon starting")
    logger.info("Vault dir: %s", obsidian_docs_dir)
    logger.info("Poll interval: %.0fs", poll_interval)

    from nauvoo.adapters.driven.filesystem_vault import FilesystemVaultAdapter
    from nauvoo.adapters.driven.google_auth import GoogleAuthAdapter
    from nauvoo.adapters.driven.google_drive_writer import GoogleDriveWriterAdapter
    from nauvoo.adapters.driving.polling_watcher import PollingWatcherAdapter
    from nauvoo.application.coordinator import VaultSyncCoordinator

    auth = GoogleAuthAdapter(
        client_secrets_file=client_secrets,
        token_file=token_file,
        scopes=GOOGLE_SCOPES,
    )
    creds = auth.get_credentials()
    logger.info("Google auth OK")

    vault = FilesystemVaultAdapter(vault_dir=obsidian_docs_dir)
    drive_writer = GoogleDriveWriterAdapter(credentials=creds)
    coordinator = VaultSyncCoordinator(vault=vault, drive=drive_writer)
    watcher = PollingWatcherAdapter(vault=vault, interval=poll_interval)

    stop_event = __import__("threading").Event()

    def _shutdown(signum, frame):
        logger.info("Shutting down...")
        watcher.stop()
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    watcher.start(on_change=coordinator.sync_files)
    logger.info("Nauvoo daemon running — watching %s", obsidian_docs_dir)

    stop_event.wait()
    logger.info("Nauvoo daemon stopped")


if __name__ == "__main__":
    main()
