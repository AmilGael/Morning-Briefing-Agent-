"""Calendar tool: list upcoming events in the next N hours."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from strands import tool

from ._google_auth import google_credentials


def _format_event_time(value: str) -> str:
    """Format an ISO-8601 event time as a local-time human-readable string."""
    if not value:
        return ""
    if "T" not in value:
        # all-day event, returned as YYYY-MM-DD
        return value
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    local = dt.astimezone()
    return local.strftime("%Y-%m-%d %H:%M %Z")


@tool
def check_calendar(hours_ahead: int = 24) -> list[dict]:
    """List Google Calendar events starting in the next `hours_ahead` hours.

    Returns a list of {title, start, end, location, attendees} dicts (local TZ).
    On auth or API failure, logs to stderr and returns [].
    """
    try:
        creds = google_credentials()
        service = build("calendar", "v3", credentials=creds)

        now = datetime.now(timezone.utc)
        time_max = now + timedelta(hours=hours_ahead)

        events = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
            .get("items", [])
        )

        results: list[dict] = []
        for event in events:
            start = event["start"].get("dateTime") or event["start"].get("date", "")
            end = event["end"].get("dateTime") or event["end"].get("date", "")
            results.append(
                {
                    "title": event.get("summary", "(no title)"),
                    "start": _format_event_time(start),
                    "end": _format_event_time(end),
                    "location": event.get("location", ""),
                    "attendees": [
                        a.get("email", "") for a in event.get("attendees", [])
                    ],
                }
            )
        return results
    except Exception as e:
        print(f"check_calendar error: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    print(json.dumps(check_calendar(), indent=2))
