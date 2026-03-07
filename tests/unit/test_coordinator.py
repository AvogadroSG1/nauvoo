from __future__ import annotations

from unittest.mock import MagicMock

from nauvoo.application.coordinator import VaultSyncCoordinator


def _make_vault(content: str) -> MagicMock:
    vault = MagicMock()
    vault.read_file.return_value = content
    return vault


def test_sync_posts_reply_and_stamps():
    content = """\
---
doc-id: fileXYZ
---
> [!comment] id:cmnt1 · Alice · 2026-03-07
> Question?
>
> > [!reply] · me · 2026-03-07
> > My answer
"""
    vault = _make_vault(content)
    drive = MagicMock()
    drive.post_reply.return_value = "reply99"

    coordinator = VaultSyncCoordinator(vault=vault, drive=drive)
    coordinator.sync_files(["/vault/my-doc.md"])

    drive.post_reply.assert_called_once_with(
        file_id="fileXYZ", comment_id="cmnt1", body="My answer"
    )
    written = vault.write_file.call_args[0][1]
    assert "id:reply99" in written


def test_sync_posts_new_comment_and_stamps():
    content = """\
---
doc-id: fileXYZ
---
> [!new-comment] · me · 2026-03-07
> My question
"""
    vault = _make_vault(content)
    drive = MagicMock()
    drive.post_comment.return_value = "cmnt99"

    coordinator = VaultSyncCoordinator(vault=vault, drive=drive)
    coordinator.sync_files(["/vault/my-doc.md"])

    drive.post_comment.assert_called_once_with(file_id="fileXYZ", body="My question")
    written = vault.write_file.call_args[0][1]
    assert "id:cmnt99" in written


def test_sync_skips_file_without_doc_id():
    content = "# No frontmatter\n"
    vault = _make_vault(content)
    drive = MagicMock()

    coordinator = VaultSyncCoordinator(vault=vault, drive=drive)
    coordinator.sync_files(["/vault/notes.md"])

    drive.post_reply.assert_not_called()
    drive.post_comment.assert_not_called()


def test_sync_skips_file_with_no_unpushed():
    content = """\
---
doc-id: fileXYZ
---
> [!comment] id:cmnt1 · Alice · 2026-03-07
> text
>
> > [!reply] id:reply1 · me · 2026-03-07
> > Already pushed
"""
    vault = _make_vault(content)
    drive = MagicMock()

    coordinator = VaultSyncCoordinator(vault=vault, drive=drive)
    coordinator.sync_files(["/vault/my-doc.md"])

    drive.post_reply.assert_not_called()
    vault.write_file.assert_not_called()
