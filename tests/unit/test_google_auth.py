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
