"""Gmail tool: list unread emails from the last N hours."""
from __future__ import annotations

import json
import sys
from email.utils import parseaddr
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from strands import tool

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
ALL_SCOPES = GMAIL_SCOPES + CALENDAR_SCOPES

ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = ROOT / "credentials.json"
TOKEN_PATH = ROOT / "token.json"


def _google_credentials() -> Credentials:
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


def _truncate(text: str, limit: int = 200) -> str:
    text = text.strip().replace("\r\n", " ").replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


@tool
def check_gmail(hours_back: int = 12) -> list[dict]:
    """List up to 50 unread emails received in the last `hours_back` hours.

    Returns a list of {sender, subject, date, snippet} dicts, snippet ≤ 200 chars.
    Hard-capped at 50 messages (no pagination) — for a morning briefing this is
    intentional; if you have >50 unread in the window, the agent will work from
    the most recent 50.

    On auth or API failure, logs to stderr and returns [] (graceful degradation
    so the agent run still produces a partial briefing).
    """
    try:
        creds = _google_credentials()
        service = build("gmail", "v1", credentials=creds)

        query = f"in:inbox is:unread newer_than:{hours_back}h"
        listing = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=50)
            .execute()
        )
        messages = listing.get("messages", [])

        results: list[dict] = []
        for msg in messages:
            full = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )
            headers = {
                h["name"]: h["value"]
                for h in full.get("payload", {}).get("headers", [])
            }
            sender_name, sender_addr = parseaddr(headers.get("From", ""))
            results.append(
                {
                    "sender": sender_name or sender_addr,
                    "subject": headers.get("Subject", ""),
                    "date": headers.get("Date", ""),
                    "snippet": _truncate(full.get("snippet", "")),
                }
            )
        return results
    except Exception as e:
        print(f"check_gmail error: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    print(json.dumps(check_gmail(), indent=2))
