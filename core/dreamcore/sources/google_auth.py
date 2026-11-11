"""Google OAuth2 (installed-app flow) for Gmail/Calendar/Photos.

One-time setup:
  1. Google Cloud Console → create OAuth client (Desktop app)
  2. Download client_secret.json into ~/.internet-dream/
  3. `dream auth` — opens browser, stores token.json next to it.

Token & secrets stay in ~/.internet-dream/ (chmod 600). Nothing is sent
anywhere except Google APIs you authorized.
"""

from __future__ import annotations

import os
from pathlib import Path

_KEY_DIR = Path.home() / ".internet-dream"
CLIENT_SECRET = _KEY_DIR / "client_secret.json"
TOKEN_FILE = _KEY_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def client_secret_path() -> Path:
    return CLIENT_SECRET


def token_path() -> Path:
    return TOKEN_FILE


def available() -> bool:
    return CLIENT_SECRET.exists()


def credentials():
    """Return authorized google-auth credentials (refreshes as needed)."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise RuntimeError(
            "Google support needs extra deps: "
            "pip install -e 'core[google]'"
        ) from e

    if not CLIENT_SECRET.exists():
        raise RuntimeError(
            f"No OAuth client at {CLIENT_SECRET}. "
            "Create a Desktop OAuth client in Google Cloud Console and "
            "save it as client_secret.json in ~/.internet-dream/"
        )

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    # re-consent if the stored token is missing any required scope
    if creds and set(creds.scopes or []) != set(SCOPES):
        creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
        os.chmod(TOKEN_FILE, 0o600)
    return creds
