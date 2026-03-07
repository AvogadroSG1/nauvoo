"""VaultSyncCoordinator — orchestrates the parse, push, stamp loop.

For each file: reads content, extracts the Google Drive ``doc-id`` from
YAML frontmatter, parses unpushed callout annotations, pushes them to
Google Drive as comments or replies, stamps the returned IDs back into
the markdown, and writes the file back to the vault.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from nauvoo.domain.callout_parser import UnpushedReply, parse_unpushed

if TYPE_CHECKING:
    from nauvoo.domain.callout_parser import UnpushedComment  # noqa: F401
from nauvoo.domain.callout_stamper import stamp_id
from nauvoo.ports.driven.drive_writer import DriveWriterPort
from nauvoo.ports.driven.vault_reader import VaultReaderPort

logger = logging.getLogger(__name__)
_DOC_ID_RE = re.compile(r"^doc-id:\s*(\S+)", re.MULTILINE)


class VaultSyncCoordinator:
    """Coordinates syncing Obsidian callout annotations to Google Drive comments."""

    def __init__(self, vault: VaultReaderPort, drive: DriveWriterPort) -> None:
        self._vault = vault
        self._drive = drive

    def sync_files(self, paths: list[str]) -> None:
        """Sync all files at *paths*, logging and swallowing per-file errors."""
        for path in paths:
            try:
                self._sync_one(path)
            except Exception:
                logger.exception("Failed to sync %s", path)

    def _sync_one(self, path: str) -> None:
        content = self._vault.read_file(path)
        doc_id = self._extract_doc_id(content)
        if not doc_id:
            return
        callouts = parse_unpushed(content)
        if not callouts:
            return
        for callout in callouts:
            if isinstance(callout, UnpushedReply):
                new_id = self._drive.post_reply(
                    file_id=doc_id,
                    comment_id=callout.parent_comment_id,
                    body=callout.body,
                )
            else:
                new_id = self._drive.post_comment(file_id=doc_id, body=callout.body)
            content = stamp_id(content, line_start=callout.line_start, new_id=new_id)
        self._vault.write_file(path, content)

    @staticmethod
    def _extract_doc_id(content: str) -> str | None:
        m = _DOC_ID_RE.search(content)
        return m.group(1) if m else None
