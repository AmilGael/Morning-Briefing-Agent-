"""Shared Google OAuth credentials helper.

Used by tools/gmail.py and tools/calendar.py. Both scopes are requested
together so a single consent flow grants both tools access — saved to
token.json for reuse on subsequent runs.
"""
from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
ALL_SCOPES = GMAIL_SCOPES + CALENDAR_SCOPES

ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = ROOT / "credentials.json"
TOKEN_PATH = ROOT / "token.json"


def google_credentials() -> Credentials:
    """Load or refresh Google OAuth credentials. Triggers consent on first run.

    If the saved token's granted scopes are missing any of `ALL_SCOPES`
    (e.g., we added a new scope since the token was issued), a refresh
    won't add them — so we force a fresh consent flow instead.
    """
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), ALL_SCOPES)

    has_required_scopes = bool(
        creds and set(ALL_SCOPES).issubset(creds.scopes or [])
    )

    if not creds or not creds.valid:
        if (
            creds
            and creds.expired
            and creds.refresh_token
            and has_required_scopes
        ):
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), ALL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return creds
