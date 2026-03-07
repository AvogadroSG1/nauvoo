from __future__ import annotations

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
        self._client_secrets_file = client_secrets_file
        self._token_file = token_file
        self._scopes = scopes

    def get_credentials(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if self._token_file.exists():
            creds = Credentials.from_authorized_user_file(
                str(self._token_file), self._scopes
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Google credentials refreshed")
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._client_secrets_file), self._scopes
                )
                creds = flow.run_local_server(port=0)
                logger.info("Google OAuth flow completed")

            self._token_file.parent.mkdir(parents=True, exist_ok=True)
            self._token_file.write_text(creds.to_json())

        return creds
