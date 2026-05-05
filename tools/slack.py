"""Slack tool: recent activity from top N most-recently-active channels."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler
from strands import tool


def _client() -> WebClient:
    load_dotenv()
    token = os.environ["SLACK_BOT_TOKEN"]
    # The env var is named SLACK_BOT_TOKEN for PRD compatibility, but the
    # value must be a User OAuth Token (xoxp-) — only user tokens see the
    # caller's channel/group history with the requested scopes.
    assert token.startswith("xoxp-"), (
        "SLACK_BOT_TOKEN must be a User OAuth Token (xoxp-…). "
        "A bot token (xoxb-…) won't see your channel history. See README §4."
    )
    client = WebClient(token=token)
    # Slack's tier-3 endpoints (conversations.history, users.info) rate-limit
    # at ~50 req/min. With many channel memberships this trips on the first
    # run. The retry handler honors Slack's Retry-After and re-issues the call
    # transparently; without it, ratelimited errors collapse the whole tool
    # to [] via the outer except.
    client.retry_handlers.append(RateLimitErrorRetryHandler(max_retry_count=3))
    return client


@tool
def check_slack(hours_back: int = 12, max_channels: int = 5) -> list[dict]:
    """Return recent activity from up to `max_channels` most-recently-active channels.

    Each item: {channel, messages: [{user, ts, text}, ...]} (≤ 5 messages each).
    Only includes channels with messages in the last `hours_back` hours.
    On auth or API failure, logs to stderr and returns [].
    """
    try:
        client = _client()
        cutoff_ts = time.time() - hours_back * 3600

        user_cache: dict[str, str] = {}

        def _user_name(user_id: str) -> str:
            if not user_id:
                return ""
            if user_id not in user_cache:
                try:
                    info = client.users_info(user=user_id)
                    user_cache[user_id] = (
                        info["user"].get("real_name")
                        or info["user"].get("name", user_id)
                    )
                except Exception:
                    user_cache[user_id] = user_id
            return user_cache[user_id]

        # 1. List channels the user is a member of (public + private)
        channels = []
        cursor = None
        while True:
            resp = client.conversations_list(
                types="public_channel,private_channel",
                limit=200,
                cursor=cursor,
                exclude_archived=True,
            )
            for ch in resp.get("channels", []):
                if ch.get("is_member") or ch.get("is_private"):
                    channels.append(ch)
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        # 2. For each channel, fetch latest activity within the time window
        candidates = []
        for ch in channels:
            history = client.conversations_history(
                channel=ch["id"], oldest=str(cutoff_ts), limit=5
            )
            msgs = history.get("messages", [])
            if not msgs:
                continue
            latest_ts = float(msgs[0]["ts"])
            candidates.append((latest_ts, ch, msgs))

        # 3. Rank by most recent activity, take top max_channels
        candidates.sort(key=lambda x: x[0], reverse=True)
        candidates = candidates[:max_channels]

        results: list[dict] = []
        for _, ch, msgs in candidates:
            formatted = []
            for m in msgs:
                ts = datetime.fromtimestamp(
                    float(m["ts"]), tz=timezone.utc
                ).astimezone()
                formatted.append(
                    {
                        "user": _user_name(m.get("user", "")),
                        "ts": ts.strftime("%Y-%m-%d %H:%M %Z"),
                        "text": m.get("text", ""),
                    }
                )
            results.append(
                {"channel": ch.get("name", ch["id"]), "messages": formatted}
            )
        return results
    except Exception as e:
        print(f"check_slack error: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    print(json.dumps(check_slack(), indent=2))
