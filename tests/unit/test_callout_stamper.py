from __future__ import annotations

from nauvoo.domain.callout_stamper import stamp_id


def test_stamp_reply_id():
    content = "> > [!reply] · me · 2026-03-07\n> > text\n"
    result = stamp_id(content, line_start=0, new_id="reply789")
    assert "> > [!reply] id:reply789 · me · 2026-03-07" in result


def test_stamp_new_comment_id():
    content = "> [!new-comment] · me · 2026-03-07\n> text\n"
    result = stamp_id(content, line_start=0, new_id="cmnt999")
    assert "> [!new-comment] id:cmnt999 · me · 2026-03-07" in result


def test_stamp_preserves_other_lines():
    content = "# Title\n\n> > [!reply] · me · 2026-03-07\n> > text\n"
    result = stamp_id(content, line_start=2, new_id="x1")
    lines = result.splitlines()
    assert lines[0] == "# Title"
    assert lines[1] == ""
    assert "id:x1" in lines[2]
    assert lines[3] == "> > text"


def test_stamp_idempotent_if_already_has_id():
    content = "> > [!reply] id:existing · me · 2026-03-07\n"
    result = stamp_id(content, line_start=0, new_id="new")
    assert "id:existing" in result
    assert "id:new" not in result
