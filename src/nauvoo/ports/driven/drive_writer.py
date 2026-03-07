from __future__ import annotations

from abc import ABC, abstractmethod


class DriveWriterPort(ABC):
    @abstractmethod
    def post_reply(self, file_id: str, comment_id: str, body: str) -> str:
        """Post a reply to an existing Drive comment. Returns the new reply ID."""

    @abstractmethod
    def post_comment(self, file_id: str, body: str) -> str:
        """Post a new top-level Drive comment. Returns the new comment ID."""
