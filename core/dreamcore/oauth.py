"""Backend Google OAuth — consent happens once against `dream serve`,
then every client (dashboard, Android, extensions, Telegram bot) shares
the stored token. No per-app Google login needed.

Flow:
  GET /auth/google/start    → redirect to Google consent
  GET /auth/google/callback → exchanges code, stores ~/.internet-dream/token.json

The OAuth client must be a *Web application* client (or Desktop/installed
client — loopback redirects are allowed) with this redirect URI
registered:
  http://127.0.0.1:8765/auth/google/callback
(or whatever host:port `dream serve` uses — update config if different).
"""

from __future__ import annotations

import os
from urllib.parse import urlencode

from .sources import google_auth

REDIRECT_PATH = "/auth/google/callback"


def redirect_uri(host: str = "127.0.0.1", port: int = 8765) -> str:
    return f"http://{host}:{port}{REDIRECT_PATH}"


def configured() -> bool:
    return google_auth.available()


def auth_url(host: str = "127.0.0.1", port: int = 8765) -> str:
    """Build the Google consent URL (does not contact Google)."""
    if not configured():
        raise RuntimeError(
            f"no OAuth client at {google_auth.CLIENT_SECRET} — create one in "
            "Google Cloud Console and save it there first")
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_secrets_file(
        str(google_auth.CLIENT_SECRET), google_auth.SCOPES,
        redirect_uri=redirect_uri(host, port))
    url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true",
        prompt="consent")
    return url


def handle_callback(code: str, host: str = "127.0.0.1", port: int = 8765):
    """Exchange the auth code and persist credentials."""
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_secrets_file(
        str(google_auth.CLIENT_SECRET), google_auth.SCOPES,
        redirect_uri=redirect_uri(host, port))
    flow.fetch_token(code=code)
    creds = flow.credentials
    google_auth.TOKEN_FILE.write_text(creds.to_json())
    os.chmod(google_auth.TOKEN_FILE, 0o600)
    return creds
