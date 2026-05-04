# Morning Briefing Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-command CLI agent (`python agent.py`) that reads Gmail, Calendar, and Slack and prints one prioritized morning briefing in five fixed sections.

**Architecture:** Strands `Agent` with three `@tool`-decorated functions (`check_gmail`, `check_calendar`, `check_slack`). LiteLLM adapter routes to OpenRouter's free model tier. Modular layout — one Python file per tool, each independently runnable for verification. Real-data validation only (no mocks), per spec.

**Tech Stack:** Python 3.10+, `strands-agents`, `litellm`, Google API Python client (Gmail + Calendar), `slack-sdk`, `python-dotenv`, OpenRouter (`openrouter/openrouter/free`).

**Spec:** `docs/superpowers/specs/2026-05-03-morning-briefing-agent-design.md`

---

## Notes on testing approach

The spec explicitly forbids mocked data: "Real data from Gmail, Calendar, Slack (not mocks)." Each tool's `__main__` block functions as the integration test against real APIs — the validation gate is human-eyeballing the JSON output. The plan's "verify" steps reflect that. This is a deliberate departure from unit-test-first TDD because mocking a Gmail/Calendar/Slack API contract would only verify our mocks, not that we hit the real services correctly.

---

### Task 1: Scaffold project structure

Set up the repository skeleton with `.gitignore` first (before any secret file exists), then dependencies, env template, and empty Python module files. Verify install works.

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `agent.py` (empty placeholder)
- Create: `test_model.py` (empty placeholder)
- Create: `tools/__init__.py` (empty)
- Create: `tools/gmail.py` (empty placeholder)
- Create: `tools/calendar.py` (empty placeholder)
- Create: `tools/slack.py` (empty placeholder)

- [ ] **Step 1: Create `.gitignore` BEFORE anything else**

```gitignore
# secrets — these must never be committed
.env
token.json
credentials.json

# python
.venv/
__pycache__/
*.pyc

# os
.DS_Store
```

- [ ] **Step 2: Create `requirements.txt`**

```
strands-agents
litellm
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
slack-sdk
python-dotenv
```

- [ ] **Step 3: Create `.env.example`**

```
OPENROUTER_API_KEY=sk-or-v1-replace-with-real-key
SLACK_BOT_TOKEN=xoxp-replace-with-real-user-token
```

- [ ] **Step 4: Create empty Python skeletons**

Run:
```bash
touch agent.py test_model.py
mkdir -p tools
touch tools/__init__.py tools/gmail.py tools/calendar.py tools/slack.py
```

- [ ] **Step 5: Create venv and install**

Run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Expected: clean install, no errors. If `strands-agents` is not found, your `pip` is likely too old — upgrade and retry.

- [ ] **Step 6: Verify install**

Run:
```bash
python -c "from strands import Agent, tool; from strands.models.litellm import LiteLLMModel; print('ok')"
```

Expected output: `ok`

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt .env.example agent.py test_model.py tools/
git commit -m "Scaffold project: gitignore, deps, empty module skeletons"
```

Verify with `git status` — `.env`, `token.json`, `credentials.json` must NOT appear (they don't exist yet, but the gitignore rule is in place for when they do).

---

### Task 2: Wire up OpenRouter and verify model connectivity

This is validation gate 1 from the spec. Confirm the free OpenRouter model is reachable before any tool is wired in.

**External setup (do this in your browser before the code steps):**

1. Go to <https://openrouter.ai> and sign up (no credit card needed for free tier).
2. Visit <https://openrouter.ai/keys> and create a new API key. Copy it.
3. Paste it into `.env` (create the file if it does not exist):

```
OPENROUTER_API_KEY=sk-or-v1-...your-real-key...
```

**Files:**
- Create: `.env` (gitignored)
- Modify: `test_model.py`

- [ ] **Step 1: Confirm `.env` exists and is gitignored**

Run:
```bash
ls -la .env && git check-ignore .env
```

Expected: `.env` listed, then `.env` echoed back (proves gitignore matches).

- [ ] **Step 2: Write `test_model.py`**

```python
"""Validation gate 1: model connectivity.

Confirms the OpenRouter free model is reachable and returns text before
any tools are wired in. Run: python test_model.py
"""
from dotenv import load_dotenv
from strands import Agent
from strands.models.litellm import LiteLLMModel

load_dotenv()

model = LiteLLMModel(
    model_id="openrouter/openrouter/free",
    params={"max_tokens": 4096},
)
agent = Agent(model=model)

response = agent("Say hello in one short sentence.")
print(response)
```

- [ ] **Step 3: Run it**

Run:
```bash
python test_model.py
```

Expected: a one-sentence greeting from the model. If you see `429 Too Many Requests`, wait 60 seconds and retry — the free tier has rate limits.

- [ ] **Step 4: Commit**

```bash
git add test_model.py
git commit -m "Add model connectivity test (validation gate 1)"
```

---

### Task 3: Implement `check_gmail` tool

This task pulls in Google OAuth setup. Both Gmail and Calendar will share the same `credentials.json` and `token.json`, so do this once now.

**External setup (do this in your browser before the code steps):**

1. Go to <https://console.cloud.google.com/>. Create a new project named e.g. `morning-briefing` (or pick an existing one).
2. Enable APIs:
   - <https://console.cloud.google.com/apis/library/gmail.googleapis.com> → Enable
   - <https://console.cloud.google.com/apis/library/calendar-json.googleapis.com> → Enable
3. Configure OAuth consent screen:
   - <https://console.cloud.google.com/apis/credentials/consent>
   - Choose **External** (works for personal Gmail accounts too).
   - Fill in app name (e.g. "Morning Briefing"), your email as user support and developer contact.
   - On scopes: leave blank (we'll request scopes in code).
   - On test users: add your own Gmail address.
4. Create OAuth client:
   - <https://console.cloud.google.com/apis/credentials> → Create Credentials → OAuth client ID
   - Application type: **Desktop app**. Name: any.
   - Click **Download JSON**. Rename the file to `credentials.json` and move it to the project root.
5. Verify file is in place: `ls credentials.json` should succeed. `git check-ignore credentials.json` should echo the filename.

**Files:**
- Modify: `tools/gmail.py`

- [ ] **Step 1: Verify `credentials.json` is present and ignored**

Run:
```bash
test -f credentials.json && git check-ignore credentials.json && echo "ok"
```

Expected: `ok`

- [ ] **Step 2: Write `tools/gmail.py`**

```python
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
    """Load or refresh Google OAuth credentials. Triggers consent on first run."""
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), ALL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
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
    """List unread emails received in the last `hours_back` hours.

    Returns a list of {sender, subject, date, snippet} dicts, snippet ≤ 200 chars.
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
```

- [ ] **Step 3: Run the standalone smoke test**

Run:
```bash
python -m tools.gmail
```

Expected on first run: a browser window opens for Google OAuth consent. Approve it. Afterwards, JSON list of unread emails prints, and `token.json` is created in the project root.

If the output is `[]`, you have no unread mail in the last 12 hours — that's a valid result. To stress-test, mark something as unread in Gmail and re-run.

- [ ] **Step 4: Verify `token.json` is gitignored**

Run:
```bash
git check-ignore token.json
```

Expected: `token.json` echoed back.

- [ ] **Step 5: Commit**

```bash
git add tools/gmail.py
git commit -m "Add check_gmail tool with shared Google OAuth flow"
```

---

### Task 4: Implement `check_calendar` tool

Reuses Google credentials from Task 3 — no new external setup.

**Files:**
- Modify: `tools/calendar.py`

- [ ] **Step 1: Write `tools/calendar.py`**

```python
"""Calendar tool: list upcoming events in the next N hours."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from strands import tool

from .gmail import _google_credentials


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
        creds = _google_credentials()
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
```

- [ ] **Step 2: Run the standalone smoke test**

Run:
```bash
python -m tools.calendar
```

Expected: JSON list of upcoming events from your primary calendar within the next 24 hours. No new OAuth prompt — the existing `token.json` already has Calendar scope.

If you see a scope-related error, delete `token.json` and re-run; the OAuth flow will re-request both scopes.

- [ ] **Step 3: Commit**

```bash
git add tools/calendar.py
git commit -m "Add check_calendar tool reusing Google OAuth credentials"
```

---

### Task 5: Implement `check_slack` tool

**External setup (do this in your browser before the code steps):**

1. Go to <https://api.slack.com/apps> → **Create New App** → **From scratch**.
2. Name it e.g. "Morning Briefing", pick your workspace.
3. In the left sidebar: **OAuth & Permissions**.
4. Scroll to **User Token Scopes** (NOT Bot Token Scopes — this is the failure mode the spec calls out). Add:
   - `channels:read`
   - `channels:history`
   - `groups:read`
   - `groups:history`
5. Scroll up and click **Install to Workspace** (or Reinstall, if you adjust scopes later). Approve.
6. Copy the **User OAuth Token** (starts with `xoxp-`). Paste into `.env`:

```
SLACK_BOT_TOKEN=xoxp-...your-real-user-token...
```

(The env var name is `SLACK_BOT_TOKEN` per the spec, even though it stores a user token. Keeping the name to match the PRD.)

**Files:**
- Modify: `tools/slack.py`

- [ ] **Step 1: Verify Slack token is in `.env`**

Run:
```bash
grep -q '^SLACK_BOT_TOKEN=xoxp-' .env && echo "ok"
```

Expected: `ok`. If it prints nothing, your token is missing or doesn't start with `xoxp-` (a `xoxb-` token is a Bot token — wrong type; redo with User Token Scopes).

- [ ] **Step 2: Write `tools/slack.py`**

```python
"""Slack tool: recent activity from top N most-recently-active channels."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from slack_sdk import WebClient
from strands import tool


def _client() -> WebClient:
    load_dotenv()
    return WebClient(token=os.environ["SLACK_BOT_TOKEN"])


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
```

- [ ] **Step 3: Run the standalone smoke test**

Run:
```bash
python -m tools.slack
```

Expected: JSON listing up to 5 channels with their last 5 messages each. If output is `[]`, either you have no channel activity in the window or scopes are wrong.

If you get an `invalid_auth` or `missing_scope` error: re-add the four scopes under **User Token Scopes** (not Bot Token Scopes), reinstall the app, and copy the new `xoxp-` token.

- [ ] **Step 4: Commit**

```bash
git add tools/slack.py
git commit -m "Add check_slack tool with channel ranking by recent activity"
```

---

### Task 6: Wire up `agent.py` and produce a real briefing

This is validation gate 3 from the spec — the end-to-end run.

**Files:**
- Modify: `tools/__init__.py`
- Modify: `agent.py`

- [ ] **Step 1: Re-export the three tools from the package**

Replace `tools/__init__.py` with:

```python
from .calendar import check_calendar
from .gmail import check_gmail
from .slack import check_slack

__all__ = ["check_gmail", "check_calendar", "check_slack"]
```

- [ ] **Step 2: Write `agent.py`**

```python
"""Morning Briefing Agent — entry point.

Runs the Strands agent loop with three read-only tools and prints a
five-section briefing.
"""
from dotenv import load_dotenv
from strands import Agent
from strands.models.litellm import LiteLLMModel

from tools import check_calendar, check_gmail, check_slack

load_dotenv()

SYSTEM_PROMPT = """\
You are a personal morning briefing assistant.

Call all three tools in this order:
1. check_gmail
2. check_calendar
3. check_slack

Then synthesize the results into a single briefing with EXACTLY these
five sections, in this order:

URGENT
UPCOMING EVENTS
SLACK HIGHLIGHTS
OTHER EMAILS
SUGGESTED ACTIONS

Be concise. If a section has nothing to report, write "(none)".
"""


def main() -> None:
    model = LiteLLMModel(
        model_id="openrouter/openrouter/free",
        params={"max_tokens": 4096},
    )
    agent = Agent(
        model=model,
        tools=[check_gmail, check_calendar, check_slack],
        system_prompt=SYSTEM_PROMPT,
    )
    response = agent("What did I miss? Give me my morning briefing.")
    print(response)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the full agent**

Run:
```bash
python agent.py
```

Expected: a printed briefing with exactly five sections (URGENT, UPCOMING EVENTS, SLACK HIGHLIGHTS, OTHER EMAILS, SUGGESTED ACTIONS) populated from real data.

Known failure modes from the spec, in case you hit them:

- `MaxTokensReachedException` → the spec already pins `max_tokens=4096`; if it still happens, lower `hours_back` defaults at the call site or trim tool outputs.
- `Invalid configuration parameters: ['max_tokens']` → `max_tokens` was placed at top level instead of inside `params={}`. Move it.
- `No endpoints found that support tool use` → the model id drifted; confirm it's exactly `openrouter/openrouter/free`.
- `429 Too Many Requests` → free tier rate limit. Wait a minute, retry.

- [ ] **Step 4: Commit**

```bash
git add tools/__init__.py agent.py
git commit -m "Wire up agent.py with three tools and five-section system prompt"
```

---

### Task 7: Replace the placeholder README with a setup walkthrough

The current README is the original PRD. Replace it with a clean, reproducible "clone-to-running" walkthrough so the spec's "reproducible setup from a clean clone in under 30 minutes" goal is actually testable.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README with setup walkthrough**

```markdown
# Morning Briefing Agent

A single-command CLI agent that reads your Gmail, Calendar, and Slack and prints one prioritized morning briefing. Personal tool, runs locally, free LLM via OpenRouter.

## What it does

`python agent.py` calls three read-only tools — `check_gmail`, `check_calendar`, `check_slack` — and synthesizes the results into one briefing with five sections:

```
URGENT
UPCOMING EVENTS
SLACK HIGHLIGHTS
OTHER EMAILS
SUGGESTED ACTIONS
```

## Setup (one-time)

Requires Python 3.10+.

### 1. Clone and install

```bash
git clone <your-fork-url>
cd Morning-Briefing-Agent-
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. OpenRouter

1. Sign up at <https://openrouter.ai> (no credit card needed for free tier).
2. Create an API key at <https://openrouter.ai/keys>.
3. Paste it into `.env` as `OPENROUTER_API_KEY=sk-or-v1-...`.

Verify: `python test_model.py` should print a one-sentence greeting.

### 3. Google (Gmail + Calendar)

1. Create a project at <https://console.cloud.google.com/>.
2. Enable the **Gmail API** and **Google Calendar API**.
3. Configure the **OAuth consent screen** as **External** and add your own Gmail as a test user.
4. Create an **OAuth client ID** of type **Desktop app**. Download the JSON, rename it to `credentials.json`, and put it in the project root.

Verify: `python -m tools.gmail` opens a browser for consent the first time, then prints unread mail. `python -m tools.calendar` should also work without a second consent prompt.

### 4. Slack

1. Create a new app at <https://api.slack.com/apps> → **From scratch**.
2. Under **OAuth & Permissions**, scroll to **User Token Scopes** (not Bot Token Scopes). Add: `channels:read`, `channels:history`, `groups:read`, `groups:history`.
3. **Install to Workspace** and copy the **User OAuth Token** (starts with `xoxp-`).
4. Paste into `.env` as `SLACK_BOT_TOKEN=xoxp-...`.

Verify: `python -m tools.slack` prints recent activity in your top channels.

### 5. Run the agent

```bash
python agent.py
```

You should see a five-section briefing built from real Gmail / Calendar / Slack data.

## Layout

```
agent.py            entry point: system prompt + Strands agent loop
test_model.py       validation gate 1: model connectivity only
tools/
  gmail.py          @tool check_gmail + standalone smoke test
  calendar.py       @tool check_calendar + standalone smoke test
  slack.py          @tool check_slack + standalone smoke test
docs/superpowers/   spec + implementation plan
```

## Security notes

- `.env`, `token.json`, `credentials.json` are gitignored. Never commit them.
- All API scopes are read-only (Gmail/Calendar `*.readonly`, Slack `*:read`/`*:history`).
- Slack uses a **user token** that carries your full identity. This is acceptable only because the agent runs on your laptop. **Never use this pattern in shared or production code.**
- If anything leaks: revoke the OpenRouter key, revoke the Google OAuth client (and delete `token.json`), reinstall the Slack app to invalidate the user token. Regenerate.

## Original design docs

- Spec: `docs/superpowers/specs/2026-05-03-morning-briefing-agent-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-03-morning-briefing-agent.md`
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Replace PRD-as-README with setup walkthrough"
```

---

## Done — what success looks like

After Task 6, `python agent.py` produces a five-section briefing built from real Gmail, Calendar, and Slack data. After Task 7, a fresh clone of the repo can reach that state in under 30 minutes by following the README.
