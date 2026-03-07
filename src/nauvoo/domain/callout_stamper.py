from __future__ import annotations

import re

_CALLOUT_TOKEN = re.compile(r"(\[!(?:reply|new-comment)\])")


def stamp_id(content: str, line_start: int, new_id: str) -> str:
    """Insert ``id:<new_id> `` into the callout header at *line_start* (0-indexed).

    If the line already contains ``id:``, return *content* unchanged (idempotent).
    """
    lines = content.split("\n")
    line = lines[line_start]
    if "id:" in line:
        return content  # already stamped, idempotent
    lines[line_start] = _CALLOUT_TOKEN.sub(rf"\1 id:{new_id}", line, count=1)
    return "\n".join(lines)
