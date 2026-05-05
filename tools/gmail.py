"""Gmail tool: list unread emails from the last N hours."""
from __future__ import annotations

import json
import sys
from email.utils import parseaddr

from googleapiclient.discovery import build
from strands import tool

from ._google_auth import google_credentials


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
        creds = google_credentials()
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
