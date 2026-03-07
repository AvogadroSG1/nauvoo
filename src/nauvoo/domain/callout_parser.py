"""Parse Obsidian markdown callouts to detect unpushed replies and comments.

Scans markdown content for ``[!reply]`` and ``[!new-comment]`` callout blocks
that lack an ``id:`` field, indicating they have not yet been pushed to
Google Drive as comments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

COMMENT_HEADER = re.compile(r"^>\s*\[!comment\]\s+id:(\S+)")
REPLY_HEADER_WITH_ID = re.compile(r"^>\s*>\s*\[!reply\]\s+id:")
REPLY_HEADER_NO_ID = re.compile(r"^>\s*>\s*\[!reply\](?!\s+id:)")
NEW_COMMENT_HEADER = re.compile(r"^>\s*\[!new-comment\](?!\s+id:)")
REPLY_BODY_LINE = re.compile(r"^>\s*>\s*(.*)")
COMMENT_BODY_LINE = re.compile(r"^>\s*(.*)")


@dataclass(frozen=True)
class UnpushedReply:
    """A reply callout that has not yet been pushed (no ``id:`` field)."""

    parent_comment_id: str
    body: str
    line_start: int
    line_end: int


@dataclass(frozen=True)
class UnpushedComment:
    """A new-comment callout that has not yet been pushed (no ``id:`` field)."""

    body: str
    line_start: int
    line_end: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_unpushed(content: str) -> list[UnpushedReply | UnpushedComment]:
    """Return all unpushed replies and new comments found in *content*.

    An unpushed reply is a ``[!reply]`` callout without an ``id:`` field.
    An unpushed comment is a ``[!new-comment]`` callout without an ``id:`` field.

    Lines are 0-indexed.  Body text is stripped of blockquote prefixes
    (``> >`` for replies, ``>`` for comments), joined with ``\\n``, and
    stripped of leading/trailing whitespace.
    """
    lines = content.splitlines()
    results: list[UnpushedReply | UnpushedComment] = []
    current_parent_id: str | None = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # Track the current parent comment id
        m = COMMENT_HEADER.match(line)
        if m:
            current_parent_id = m.group(1)
            i += 1
            continue

        # Skip pushed replies (they have id:)
        if REPLY_HEADER_WITH_ID.match(line):
            i += 1
            continue

        # Unpushed reply
        if REPLY_HEADER_NO_ID.match(line):
            start = i
            i += 1
            body_lines: list[str] = []
            while i < len(lines):
                bm = REPLY_BODY_LINE.match(lines[i])
                if bm:
                    body_lines.append(bm.group(1))
                    i += 1
                else:
                    break
            end = i - 1 if body_lines else start
            results.append(
                UnpushedReply(
                    parent_comment_id=current_parent_id or "",
                    body="\n".join(body_lines).strip(),
                    line_start=start,
                    line_end=end,
                )
            )
            continue

        # Unpushed new comment
        if NEW_COMMENT_HEADER.match(line):
            start = i
            i += 1
            body_lines = []
            while i < len(lines):
                bm = COMMENT_BODY_LINE.match(lines[i])
                if bm:
                    body_lines.append(bm.group(1))
                    i += 1
                else:
                    break
            end = i - 1 if body_lines else start
            results.append(
                UnpushedComment(
                    body="\n".join(body_lines).strip(),
                    line_start=start,
                    line_end=end,
                )
            )
            continue

        i += 1

    return results
