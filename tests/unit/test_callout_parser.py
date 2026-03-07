from __future__ import annotations

from nauvoo.domain.callout_parser import UnpushedComment, UnpushedReply, parse_unpushed


def test_no_unpushed_returns_empty():
    content = """> [!comment] id:abc123 · Alice · 2026-03-07
> Some text
>
> > [!reply] id:reply456 · Alice · 2026-03-07
> > A reply
"""
    assert parse_unpushed(content) == []


def test_unpushed_reply_detected():
    content = """> [!comment] id:abc123 · Alice · 2026-03-07
> Some text
>
> > [!reply] · me · 2026-03-07
> > My reply text
"""
    result = parse_unpushed(content)
    assert len(result) == 1
    r = result[0]
    assert isinstance(r, UnpushedReply)
    assert r.parent_comment_id == "abc123"
    assert "My reply text" in r.body


def test_unpushed_new_comment_detected():
    content = """> [!new-comment] · me · 2026-03-07
> My new comment
"""
    result = parse_unpushed(content)
    assert len(result) == 1
    c = result[0]
    assert isinstance(c, UnpushedComment)
    assert "My new comment" in c.body


def test_multiline_reply_body():
    content = """> [!comment] id:abc123 · Alice · 2026-03-07
> text
>
> > [!reply] · me · 2026-03-07
> > Line one
> > Line two
"""
    result = parse_unpushed(content)
    assert len(result) == 1
    assert "Line one" in result[0].body
    assert "Line two" in result[0].body


def test_line_numbers_correct():
    content = """> [!comment] id:abc123 · Alice · 2026-03-07
> text
>
> > [!reply] · me · 2026-03-07
> > My reply
"""
    result = parse_unpushed(content)
    assert result[0].line_start == 3  # 0-indexed
    assert result[0].line_end == 4
