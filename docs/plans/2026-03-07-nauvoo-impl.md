# Nauvoo Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a push daemon that watches Obsidian markdown files written by Ring Station and pushes `[!reply]` and `[!new-comment]` callouts (those without an `id:` field) to Google Drive via the Drive Comments API, then stamps the returned IDs back into the file.

**Architecture:** Hexagonal — `VaultWatcherPort` (driving) polls OBSIDIAN_DOCS_DIR every N seconds, finds changed `.md` files, parses unpushed callouts with `CalloutParser` (domain), dispatches to `VaultSyncCoordinator` (application) which calls `DriveWriterPort` (driven) to push and `VaultReaderPort` (driven) to stamp.

**Tech Stack:** Python 3.12, uv, google-api-python-client, pytest, ruff

---

## Task 1: Domain — CalloutParser

Parse a markdown file's comment section for unpushed callouts (those without `id:` in their header line).

**Files:**
- Create: `src/nauvoo/domain/callout_parser.py`
- Create: `tests/unit/test_callout_parser.py`

**Callout format reference:**

Ring Station writes:
```
> [!comment] id:abc123 · Alice · 2026-03-07
> Comment text
>
> > [!reply] id:reply456 · Alice · 2026-03-07
> > Reply text
```

User writes (unpushed — no id:):
```
> > [!reply] · me · 2026-03-07
> > My reply text
```

```
> [!new-comment] · me · 2026-03-07
> My new comment text
```

**Data models:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class UnpushedReply:
    parent_comment_id: str   # id: field from the [!comment] header above
    body: str                # reply text (stripped of > prefixes)
    line_start: int          # 0-indexed line number of the [!reply] header line
    line_end: int            # 0-indexed line number of last line of block

@dataclass(frozen=True)
class UnpushedComment:
    body: str
    line_start: int
    line_end: int
```

**Parser function:**

```python
def parse_unpushed(content: str) -> list[UnpushedReply | UnpushedComment]:
    ...
```

**Step 1: Write failing tests**

```python
# tests/unit/test_callout_parser.py
from nauvoo.domain.callout_parser import parse_unpushed, UnpushedReply, UnpushedComment

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
    assert result[0].line_start == 3   # 0-indexed
    assert result[0].line_end == 4
```

**Step 2: Run to verify failures**

```bash
cd ~/nauvoo && uv run pytest tests/unit/test_callout_parser.py -v
```
Expected: `ImportError` or `ModuleNotFoundError`

**Step 3: Implement CalloutParser**

Key algorithm:
- Scan lines, track current `parent_comment_id` when a `[!comment] id:X` header is seen
- When `[!reply]` without `id:` is found, accumulate body lines until next callout header or non-`>` line
- When `[!new-comment]` without `id:` is found, accumulate body similarly
- Body extraction: strip leading `> > ` (2-level) or `> ` (1-level) prefix from each line

Regex helpers:
```python
import re
COMMENT_HEADER = re.compile(r"^>\s*\[!comment\]\s+id:(\S+)")
REPLY_HEADER_WITH_ID = re.compile(r"^>\s*>\s*\[!reply\]\s+id:")
REPLY_HEADER_NO_ID = re.compile(r"^>\s*>\s*\[!reply\](?!\s+id:)")
NEW_COMMENT_HEADER = re.compile(r"^>\s*\[!new-comment\](?!\s+id:)")
REPLY_BODY_LINE = re.compile(r"^>\s*>\s*(.*)")
COMMENT_BODY_LINE = re.compile(r"^>\s*(.*)")
```

**Step 4: Run to verify passing**

```bash
uv run pytest tests/unit/test_callout_parser.py -v
```
Expected: all PASS

**Step 5: Commit**

```bash
cd ~/nauvoo
git add src/nauvoo/domain/callout_parser.py tests/unit/test_callout_parser.py
git commit -m "$(cat <<'EOF'
feat: add CalloutParser domain — detects unpushed reply/comment callouts

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Domain — CalloutStamper

Write the inverse: given a file's content, an unpushed callout (by line range), and a returned Drive ID, stamp the `id:` field into the callout header line.

**Files:**
- Create: `src/nauvoo/domain/callout_stamper.py`
- Create: `tests/unit/test_callout_stamper.py`

**Function:**

```python
def stamp_id(content: str, line_start: int, new_id: str) -> str:
    """Insert `id:<new_id> ` into the callout header at line_start."""
    ...
```

Before: `> > [!reply] · me · 2026-03-07`
After:  `> > [!reply] id:reply789 · me · 2026-03-07`

Before: `> [!new-comment] · me · 2026-03-07`
After:  `> [!new-comment] id:cmnt999 · me · 2026-03-07`

**Step 1: Write failing tests**

```python
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
    # Should not double-stamp; existing id preserved
    assert "id:existing" in result
    assert "id:new" not in result
```

**Step 2: Run to verify failures**

```bash
uv run pytest tests/unit/test_callout_stamper.py -v
```

**Step 3: Implement**

Algorithm: split on `\n`, find the target line, insert ` id:<new_id>` after `[!reply]` or `[!new-comment]` token (but only if no `id:` already present).

```python
import re

_CALLOUT_TOKEN = re.compile(r"(\[!(?:reply|new-comment)\])")

def stamp_id(content: str, line_start: int, new_id: str) -> str:
    lines = content.split("\n")
    line = lines[line_start]
    if "id:" in line:
        return content  # already stamped
    lines[line_start] = _CALLOUT_TOKEN.sub(rf"\1 id:{new_id}", line, count=1)
    return "\n".join(lines)
```

**Step 4: Run tests**

```bash
uv run pytest tests/unit/test_callout_stamper.py -v
```

**Step 5: Commit**

```bash
git add src/nauvoo/domain/callout_stamper.py tests/unit/test_callout_stamper.py
git commit -m "$(cat <<'EOF'
feat: add CalloutStamper domain — stamps Drive IDs into callout headers

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Ports

Define the three abstract port interfaces.

**Files:**
- Create: `src/nauvoo/ports/driven/vault_reader.py`
- Create: `src/nauvoo/ports/driven/drive_writer.py`
- Create: `src/nauvoo/ports/driving/vault_watcher.py`

**VaultReaderPort:**

```python
# src/nauvoo/ports/driven/vault_reader.py
from __future__ import annotations
from abc import ABC, abstractmethod

class VaultReaderPort(ABC):
    @abstractmethod
    def read_file(self, path: str) -> str:
        """Read a markdown file's content."""

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """Write (overwrite) a markdown file's content."""

    @abstractmethod
    def list_md_files(self) -> list[str]:
        """Return absolute paths of all .md files in the watched directory."""
```

**DriveWriterPort:**

```python
# src/nauvoo/ports/driven/drive_writer.py
from __future__ import annotations
from abc import ABC, abstractmethod

class DriveWriterPort(ABC):
    @abstractmethod
    def post_reply(self, file_id: str, comment_id: str, body: str) -> str:
        """Post a reply to an existing Drive comment. Returns the new reply ID."""

    @abstractmethod
    def post_comment(self, file_id: str, body: str) -> str:
        """Post a new top-level Drive comment. Returns the new comment ID."""
```

**VaultWatcherPort:**

```python
# src/nauvoo/ports/driving/vault_watcher.py
from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Callable

class VaultWatcherPort(ABC):
    @abstractmethod
    def start(self, on_change: Callable[[list[str]], None]) -> None:
        """Start watching. Calls on_change with list of changed file paths."""

    @abstractmethod
    def stop(self) -> None:
        """Stop watching."""
```

No tests needed for abstract ports — they are interfaces. Write the port files, no test file needed.

**Step 1: Write all three port files**

**Step 2: Verify ruff passes**

```bash
uv run ruff check src/nauvoo/ports/
```

**Step 3: Commit**

```bash
git add src/nauvoo/ports/
git commit -m "$(cat <<'EOF'
feat: define VaultReaderPort, DriveWriterPort, VaultWatcherPort interfaces

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Application — VaultSyncCoordinator

Orchestrates the push loop: receives a list of changed file paths, parses each for unpushed callouts, pushes them, stamps IDs back.

**Files:**
- Create: `src/nauvoo/application/coordinator.py`
- Create: `tests/unit/test_coordinator.py`

**Class:**

```python
class VaultSyncCoordinator:
    def __init__(
        self,
        vault: VaultReaderPort,
        drive: DriveWriterPort,
        doc_id_map: dict[str, str],  # filename stem → Drive file ID
    ) -> None: ...

    def sync_files(self, paths: list[str]) -> None:
        """For each path, parse callouts, push, stamp, write back."""
```

`doc_id_map` maps filename stem (e.g. `"my-doc-slug"`) to Drive file ID (e.g. `"1J7x3w..."`). The coordinator reads this from the markdown frontmatter's `doc-id` field (Ring Station writes it).

**Step 1: Write failing tests**

```python
from unittest.mock import MagicMock, patch
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
```

**Step 2: Run to verify failures**

```bash
uv run pytest tests/unit/test_coordinator.py -v
```

**Step 3: Implement VaultSyncCoordinator**

```python
from __future__ import annotations
import logging
import re
from nauvoo.domain.callout_parser import parse_unpushed, UnpushedReply, UnpushedComment
from nauvoo.domain.callout_stamper import stamp_id
from nauvoo.ports.driven.vault_reader import VaultReaderPort
from nauvoo.ports.driven.drive_writer import DriveWriterPort

logger = logging.getLogger(__name__)
_DOC_ID_RE = re.compile(r"^doc-id:\s*(\S+)", re.MULTILINE)

class VaultSyncCoordinator:
    def __init__(self, vault: VaultReaderPort, drive: DriveWriterPort) -> None:
        self._vault = vault
        self._drive = drive

    def sync_files(self, paths: list[str]) -> None:
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
                    file_id=doc_id, comment_id=callout.parent_comment_id, body=callout.body
                )
            else:
                new_id = self._drive.post_comment(file_id=doc_id, body=callout.body)
            content = stamp_id(content, line_start=callout.line_start, new_id=new_id)
        self._vault.write_file(path, content)

    def _extract_doc_id(self, content: str) -> str | None:
        m = _DOC_ID_RE.search(content)
        return m.group(1) if m else None
```

**Step 4: Run tests**

```bash
uv run pytest tests/unit/test_coordinator.py -v
```

**Step 5: Commit**

```bash
git add src/nauvoo/application/coordinator.py tests/unit/test_coordinator.py
git commit -m "$(cat <<'EOF'
feat: add VaultSyncCoordinator — orchestrates parse, push, stamp loop

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Driven Adapters — FilesystemVaultAdapter + PollingWatcherAdapter

Two concrete adapters: one reads/writes files, one polls for changes.

**Files:**
- Create: `src/nauvoo/adapters/driven/filesystem_vault.py`
- Create: `src/nauvoo/adapters/driving/polling_watcher.py`
- Create: `tests/unit/test_filesystem_vault.py`

**FilesystemVaultAdapter:**

```python
class FilesystemVaultAdapter(VaultReaderPort):
    def __init__(self, vault_dir: Path) -> None: ...
    def read_file(self, path: str) -> str: ...
    def write_file(self, path: str, content: str) -> None: ...
    def list_md_files(self) -> list[str]: ...
```

**PollingWatcherAdapter** — polls every `interval` seconds, tracks mtimes:

```python
class PollingWatcherAdapter(VaultWatcherPort):
    def __init__(self, vault: VaultReaderPort, interval: float = 30.0) -> None: ...
    def start(self, on_change: Callable[[list[str]], None]) -> None: ...
    def stop(self) -> None: ...
```

On each poll: call `vault.list_md_files()`, compare mtime of each path against stored snapshot. Files with newer mtime go into the changed list. Call `on_change(changed)` if non-empty. Update snapshot.

**Step 1: Write failing tests for FilesystemVaultAdapter**

```python
# tests/unit/test_filesystem_vault.py
from pathlib import Path
from nauvoo.adapters.driven.filesystem_vault import FilesystemVaultAdapter

def test_read_write_roundtrip(tmp_path):
    adapter = FilesystemVaultAdapter(vault_dir=tmp_path)
    (tmp_path / "doc.md").write_text("hello")
    assert adapter.read_file(str(tmp_path / "doc.md")) == "hello"
    adapter.write_file(str(tmp_path / "doc.md"), "updated")
    assert (tmp_path / "doc.md").read_text() == "updated"

def test_list_md_files(tmp_path):
    (tmp_path / "a.md").write_text("")
    (tmp_path / "b.md").write_text("")
    (tmp_path / "other.txt").write_text("")
    adapter = FilesystemVaultAdapter(vault_dir=tmp_path)
    files = adapter.list_md_files()
    names = {Path(f).name for f in files}
    assert names == {"a.md", "b.md"}
```

**Step 2: Run to verify failures**

```bash
uv run pytest tests/unit/test_filesystem_vault.py -v
```

**Step 3: Implement both adapters**

FilesystemVaultAdapter: straightforward `Path.read_text` / `Path.write_text` / `glob("**/*.md")`.

PollingWatcherAdapter: use `threading.Thread` + `threading.Event` for stop signal. Each iteration: sleep `interval`, list files, compare mtimes.

**Step 4: Run filesystem tests**

```bash
uv run pytest tests/unit/test_filesystem_vault.py -v
```

**Step 5: Commit**

```bash
git add src/nauvoo/adapters/driven/filesystem_vault.py src/nauvoo/adapters/driving/polling_watcher.py tests/unit/test_filesystem_vault.py
git commit -m "$(cat <<'EOF'
feat: add FilesystemVaultAdapter and PollingWatcherAdapter

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Driven Adapter — GoogleDriveWriterAdapter

Wraps the Drive API `comments().create()` and `replies().create()`.

**Files:**
- Create: `src/nauvoo/adapters/driven/google_drive_writer.py`
- Create: `tests/unit/test_google_drive_writer.py`

**Class:**

```python
class GoogleDriveWriterAdapter(DriveWriterPort):
    def __init__(self, credentials) -> None:
        from googleapiclient.discovery import build
        self._drive = build("drive", "v3", credentials=credentials)

    def post_reply(self, file_id: str, comment_id: str, body: str) -> str:
        result = self._drive.comments().replies().create(
            fileId=file_id,
            commentId=comment_id,
            body={"content": body},
            fields="id",
        ).execute()
        return result["id"]

    def post_comment(self, file_id: str, body: str) -> str:
        result = self._drive.comments().create(
            fileId=file_id,
            body={"content": body},
            fields="id",
        ).execute()
        return result["id"]
```

**Step 1: Write failing tests using `__new__` bypass pattern**

```python
from unittest.mock import MagicMock
from nauvoo.adapters.driven.google_drive_writer import GoogleDriveWriterAdapter

def _make_adapter():
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
```

**Step 2: Run to verify failures**

```bash
uv run pytest tests/unit/test_google_drive_writer.py -v
```

**Step 3: Implement GoogleDriveWriterAdapter**

**Step 4: Run tests**

```bash
uv run pytest tests/unit/test_google_drive_writer.py -v
```

**Step 5: Commit**

```bash
git add src/nauvoo/adapters/driven/google_drive_writer.py tests/unit/test_google_drive_writer.py
git commit -m "$(cat <<'EOF'
feat: add GoogleDriveWriterAdapter — posts replies and comments via Drive API

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: GoogleAuthAdapter + daemon entry point

Thin auth adapter (reuses Ring Station's pattern, no shared code) and the `daemon.py` entry point.

**Files:**
- Create: `src/nauvoo/adapters/driven/google_auth.py`
- Create: `src/nauvoo/daemon.py`

**GoogleAuthAdapter** — same pattern as Ring Station (~20 lines):

```python
class GoogleAuthAdapter:
    def __init__(self, client_secrets_file: Path, token_file: Path, scopes: list[str]) -> None:
        ...

    def get_credentials(self):
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        # load from token_file, refresh if needed, run flow if missing
        ...
```

**daemon.py** — composition root, wires everything, starts poller:

```python
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive",  # read+write for comments
]

def main() -> None:
    obsidian_docs_dir = Path(os.environ["OBSIDIAN_DOCS_DIR"])
    poll_interval = float(os.environ.get("NAUVOO_POLL_INTERVAL", "30"))
    ...
    vault = FilesystemVaultAdapter(vault_dir=obsidian_docs_dir)
    drive_writer = GoogleDriveWriterAdapter(credentials=creds)
    coordinator = VaultSyncCoordinator(vault=vault, drive=drive_writer)
    watcher = PollingWatcherAdapter(vault=vault, interval=poll_interval)
    watcher.start(on_change=coordinator.sync_files)
    # block until KeyboardInterrupt
```

No unit tests for daemon.py (composition root) or GoogleAuthAdapter (OAuth flow). Verify by running manually.

**Step 1: Write GoogleAuthAdapter**

Copy pattern from Ring Station `adapters/driven/google_auth.py` — DO NOT import from Ring Station, copy the implementation.

**Step 2: Write daemon.py**

**Step 3: Verify ruff**

```bash
uv run ruff check src/nauvoo/
```

**Step 4: Smoke test (optional — requires credentials)**

```bash
OBSIDIAN_DOCS_DIR=~/ObsidianNotes/Work/16-Google-Docs \
uv run nauvoo
```
Expected: daemon starts, logs polling interval, begins polling.

**Step 5: Commit**

```bash
git add src/nauvoo/adapters/driven/google_auth.py src/nauvoo/daemon.py
git commit -m "$(cat <<'EOF'
feat: add GoogleAuthAdapter and daemon entry point — wires and starts Nauvoo

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: CONTRIBUTING.md + uv sync

Write CONTRIBUTING.md and verify the full test suite passes.

**Files:**
- Create: `CONTRIBUTING.md`

**Step 1: Write CONTRIBUTING.md**

Mirror Ring Station's structure: Development Setup, Architecture Overview, TDD rules, Code Style, Commit Format, Environment Variables.

**Step 2: Install dependencies and run full suite**

```bash
cd ~/nauvoo
uv sync --extra google --extra dev
uv run pytest
uv run ruff check src/ tests/
```

Expected: all tests pass, ruff clean.

**Step 3: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "$(cat <<'EOF'
docs: add CONTRIBUTING.md

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```
