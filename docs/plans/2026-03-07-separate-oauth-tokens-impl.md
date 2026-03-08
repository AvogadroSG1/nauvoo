# Separate OAuth Tokens Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give Nauvoo and Ring Station separate OAuth token files so they stop overwriting each other's scopes.

**Architecture:** Change the default token path constant in each project's daemon.py to an XDG-style path (`~/.config/<project>/token.json`). Add scope-checking to Nauvoo's GoogleAuthAdapter to match Ring Station's defensive guard. Update docs.

**Tech Stack:** Python, google-auth, google-auth-oauthlib

---

### Task 1: Add scope checking to Nauvoo's GoogleAuthAdapter

**Files:**
- Test: `tests/unit/test_google_auth.py` (create)
- Modify: `src/nauvoo/adapters/driven/google_auth.py`

**Step 1: Write the failing tests**

Create `tests/unit/test_google_auth.py`:

```python
"""Tests for GoogleAuthAdapter."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_google_auth():
    """Stub google.auth and google_auth_oauthlib so get_credentials() can run."""
    mock_google = MagicMock()
    mock_oauthlib = MagicMock()
    modules = {
        "google": mock_google,
        "google.auth": mock_google.auth,
        "google.auth.transport": mock_google.auth.transport,
        "google.auth.transport.requests": mock_google.auth.transport.requests,
        "google.oauth2": mock_google.oauth2,
        "google.oauth2.credentials": mock_google.oauth2.credentials,
        "google_auth_oauthlib": mock_oauthlib,
        "google_auth_oauthlib.flow": mock_oauthlib.flow,
    }
    with patch.dict(sys.modules, modules):
        sys.modules.pop("nauvoo.adapters.driven.google_auth", None)
        from nauvoo.adapters.driven.google_auth import GoogleAuthAdapter

        yield GoogleAuthAdapter


class TestScopeChecking:
    def test_raises_if_token_missing_scopes(self, mock_google_auth, tmp_path):
        token_file = tmp_path / "token.json"
        token_file.write_text(
            json.dumps({"scopes": ["https://www.googleapis.com/auth/drive.readonly"]})
        )

        adapter = mock_google_auth(
            client_secrets_file=tmp_path / "secrets.json",
            token_file=token_file,
            scopes=["https://www.googleapis.com/auth/drive"],
        )

        with pytest.raises(ValueError, match="missing required scopes"):
            adapter.get_credentials()

    def test_passes_when_all_scopes_present(self, mock_google_auth, tmp_path):
        token_file = tmp_path / "token.json"
        token_file.write_text(
            json.dumps({"scopes": ["https://www.googleapis.com/auth/drive"]})
        )

        adapter = mock_google_auth(
            client_secrets_file=tmp_path / "secrets.json",
            token_file=token_file,
            scopes=["https://www.googleapis.com/auth/drive"],
        )

        # Should not raise — scopes match
        adapter.get_credentials()

    def test_raises_file_not_found_when_no_secrets(self, mock_google_auth, tmp_path):
        adapter = mock_google_auth(
            client_secrets_file=tmp_path / "nonexistent_secrets.json",
            token_file=tmp_path / "nonexistent_token.json",
            scopes=["https://www.googleapis.com/auth/drive"],
        )

        with pytest.raises(FileNotFoundError):
            adapter.get_credentials()
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/poconnor/nauvoo && uv run pytest tests/unit/test_google_auth.py -v`
Expected: FAIL — `_check_scopes` does not exist, `FileNotFoundError` not raised.

**Step 3: Add `_check_scopes()` and `FileNotFoundError` guard to GoogleAuthAdapter**

Modify `src/nauvoo/adapters/driven/google_auth.py` to match this:

```python
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class GoogleAuthAdapter:
    def __init__(
        self,
        client_secrets_file: Path,
        token_file: Path,
        scopes: list[str],
    ) -> None:
        self._client_secrets_file = Path(client_secrets_file)
        self._token_file = Path(token_file)
        self._scopes = scopes

    def get_credentials(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if self._token_file.exists():
            has_scopes, missing = self._check_scopes()
            if not has_scopes:
                raise ValueError(
                    f"Token missing required scopes: {missing}. "
                    f"Delete {self._token_file} and re-run to authorize."
                )
            creds = Credentials.from_authorized_user_file(
                str(self._token_file), self._scopes
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Google credentials refreshed")
            else:
                if not self._client_secrets_file.exists():
                    raise FileNotFoundError(
                        f"OAuth client secrets not found at {self._client_secrets_file}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._client_secrets_file), self._scopes
                )
                creds = flow.run_local_server(port=0)
                logger.info("Google OAuth flow completed")

            self._token_file.parent.mkdir(parents=True, exist_ok=True)
            self._token_file.write_text(creds.to_json())

        return creds

    def _check_scopes(self) -> tuple[bool, set[str]]:
        """Check if token has all required scopes."""
        try:
            token_data = json.loads(self._token_file.read_text())
            granted = set(token_data.get("scopes", []))
            required = set(self._scopes)
            missing = required - granted
            return len(missing) == 0, missing
        except (json.JSONDecodeError, OSError):
            return False, set(self._scopes)
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/poconnor/nauvoo && uv run pytest tests/unit/test_google_auth.py -v`
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add tests/unit/test_google_auth.py src/nauvoo/adapters/driven/google_auth.py
git commit -m "feat: add scope checking to Nauvoo GoogleAuthAdapter

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Change Nauvoo default token path to XDG

**Files:**
- Modify: `src/nauvoo/daemon.py:27-36`

**Step 1: Update the DEFAULT_TOKEN_FILE constant**

In `src/nauvoo/daemon.py`, replace lines 27-36:

```python
# Before:
DEFAULT_TOKEN_FILE = (
    Path.home()
    / "ObsidianNotes"
    / "Work"
    / "02-Technical"
    / "Code"
    / "GoogleDataExtraction"
    / "credentials"
    / "token.json"
)

# After:
DEFAULT_TOKEN_FILE = Path.home() / ".config" / "nauvoo" / "token.json"
```

Also update the docstring at line 11:

```python
# Before:
#     GOOGLE_TOKEN_FILE: Path to OAuth token.json (default: ~/ObsidianNotes/Work/.../token.json)
# After:
#     GOOGLE_TOKEN_FILE: Path to OAuth token.json (default: ~/.config/nauvoo/token.json)
```

**Step 2: Run the full Nauvoo test suite**

Run: `cd /Users/poconnor/nauvoo && uv run pytest tests/ -v`
Expected: All tests PASS (no test depends on the default path constant).

**Step 3: Commit**

```bash
git add src/nauvoo/daemon.py
git commit -m "feat: change Nauvoo default token path to ~/.config/nauvoo/token.json

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Update Nauvoo docs

**Files:**
- Modify: `README.md:71`
- Modify: `CONTRIBUTING.md:128`

**Step 1: Update README.md env var table**

Change line 71 from:
```
| `GOOGLE_TOKEN_FILE` | `~/ObsidianNotes/.../token.json` | OAuth token |
```
To:
```
| `GOOGLE_TOKEN_FILE` | `~/.config/nauvoo/token.json` | OAuth token |
```

**Step 2: Update CONTRIBUTING.md env var table**

Change line 128 from:
```
| `GOOGLE_TOKEN_FILE` | `~/ObsidianNotes/.../token.json` | OAuth token |
```
To:
```
| `GOOGLE_TOKEN_FILE` | `~/.config/nauvoo/token.json` | OAuth token |
```

**Step 3: Commit**

```bash
git add README.md CONTRIBUTING.md
git commit -m "docs: update Nauvoo token path in README and CONTRIBUTING

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Change Ring Station default token path to XDG

**Files:**
- Modify: `/Users/poconnor/ringstation/src/ring_station/daemon.py:30-39`

**Step 1: Update the DEFAULT_TOKEN_FILE constant**

In `/Users/poconnor/ringstation/src/ring_station/daemon.py`, replace lines 30-39:

```python
# Before:
DEFAULT_TOKEN_FILE = (
    Path.home()
    / "ObsidianNotes"
    / "Work"
    / "02-Technical"
    / "Code"
    / "GoogleDataExtraction"
    / "credentials"
    / "token.json"
)

# After:
DEFAULT_TOKEN_FILE = Path.home() / ".config" / "ring-station" / "token.json"
```

**Step 2: Run the full Ring Station test suite**

Run: `cd /Users/poconnor/ringstation && uv run pytest tests/ -v`
Expected: All tests PASS.

**Step 3: Commit**

```bash
cd /Users/poconnor/ringstation
git checkout -b feat/separate-oauth-tokens
git add src/ring_station/daemon.py
git commit -m "feat: change Ring Station default token path to ~/.config/ring-station/token.json

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Update Ring Station docs

**Files:**
- Modify: `/Users/poconnor/ringstation/README.md:415`
- Modify: `/Users/poconnor/ringstation/CONTRIBUTING.md:161`
- Modify: `/Users/poconnor/ringstation/CLAUDE.md:73`

**Step 1: Update README.md env var table**

Change line 415 from:
```
| `GOOGLE_TOKEN_FILE` | `.../GoogleDataExtraction/credentials/token.json` | OAuth token cache |
```
To:
```
| `GOOGLE_TOKEN_FILE` | `~/.config/ring-station/token.json` | OAuth token cache |
```

**Step 2: Update CONTRIBUTING.md env var table**

Change line 161 from:
```
| `GOOGLE_TOKEN_FILE` | `~/ObsidianNotes/.../token.json` | OAuth token |
```
To:
```
| `GOOGLE_TOKEN_FILE` | `~/.config/ring-station/token.json` | OAuth token |
```

**Step 3: Update CLAUDE.md env var table**

Change line 73 from:
```
| GOOGLE_TOKEN_FILE | .../GoogleDataExtraction/credentials/token.json | OAuth token cache |
```
To:
```
| GOOGLE_TOKEN_FILE | ~/.config/ring-station/token.json | OAuth token cache |
```

**Step 4: Commit**

```bash
cd /Users/poconnor/ringstation
git add README.md CONTRIBUTING.md CLAUDE.md
git commit -m "docs: update Ring Station token path in README, CONTRIBUTING, and CLAUDE.md

Co-Authored-By: Peter O'Connor <poconnor@stackoverflow.com>
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Delete the old shared token file

**Step 1: Remove the old token**

```bash
rm ~/ObsidianNotes/Work/02-Technical/Code/GoogleDataExtraction/credentials/token.json
```

This forces both projects to re-authenticate on next run, writing their tokens to the new XDG paths.
