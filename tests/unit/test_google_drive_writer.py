from __future__ import annotations

from unittest.mock import MagicMock

from nauvoo.adapters.driven.google_drive_writer import GoogleDriveWriterAdapter


def _make_adapter() -> GoogleDriveWriterAdapter:
    adapter = GoogleDriveWriterAdapter.__new__(GoogleDriveWriterAdapter)
    adapter._drive = MagicMock()
    return adapter


def test_post_reply_calls_api():
    adapter = _make_adapter()
    replies_mock = adapter._drive.comments.return_value.replies.return_value
    replies_mock.create.return_value.execute.return_value = {"id": "reply99"}

    result = adapter.post_reply(file_id="fileXYZ", comment_id="cmnt1", body="My answer")

    assert result == "reply99"
    replies_mock.create.assert_called_once_with(
        fileId="fileXYZ",
        commentId="cmnt1",
        body={"content": "My answer"},
        fields="id",
    )


def test_post_comment_calls_api():
    adapter = _make_adapter()
    comments_mock = adapter._drive.comments.return_value
    comments_mock.create.return_value.execute.return_value = {"id": "cmnt99"}

    result = adapter.post_comment(file_id="fileXYZ", body="My question")

    assert result == "cmnt99"
    comments_mock.create.assert_called_once_with(
        fileId="fileXYZ",
        body={"content": "My question"},
        fields="id",
    )
