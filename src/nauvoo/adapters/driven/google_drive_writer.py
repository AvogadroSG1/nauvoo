from __future__ import annotations

from nauvoo.ports.driven.drive_writer import DriveWriterPort


class GoogleDriveWriterAdapter(DriveWriterPort):
    def __init__(self, credentials) -> None:
        from googleapiclient.discovery import build

        self._drive = build("drive", "v3", credentials=credentials)

    def post_reply(self, file_id: str, comment_id: str, body: str) -> str:
        """Post a reply to an existing Drive comment. Returns the new reply ID."""
        result = (
            self._drive.comments()
            .replies()
            .create(
                fileId=file_id,
                commentId=comment_id,
                body={"content": body},
                fields="id",
            )
            .execute()
        )
        return result["id"]

    def post_comment(self, file_id: str, body: str) -> str:
        """Post a new top-level Drive comment. Returns the new comment ID."""
        result = (
            self._drive.comments()
            .create(
                fileId=file_id,
                body={"content": body},
                fields="id",
            )
            .execute()
        )
        return result["id"]
