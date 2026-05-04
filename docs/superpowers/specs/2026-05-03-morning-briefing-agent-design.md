# Morning Briefing Agent — Design

**Date:** 2026-05-03
**Status:** Approved for implementation

## Purpose

A single-command CLI agent that reads my Gmail, Calendar, and Slack and prints one prioritized morning briefing. Personal tool, runs locally, free LLM via OpenRouter. The PRD in `README.md` is the authoritative product spec; this document captures the implementation-level decisions that the PRD does not pin down.

## Scope

In scope:

- One Python project, runnable with `python agent.py`.
- Three read-only tools: Gmail unread, Calendar upcoming, Slack recent activity.
- Five-section briefing output: URGENT, UPCOMING EVENTS, SLACK HIGHLIGHTS, OTHER EMAILS, SUGGESTED ACTIONS.
- Setup walkthrough for OpenRouter, Google Cloud, and Slack from zero.

Out of scope (explicit non-goals from PRD):

- Deployment, multi-user, scheduled runs, GUI.
- Any write actions — no replies, no event creation, no Slack posts.
- Real-time or push delivery.

## File Layout

```
Morning-Briefing-Agent-/
├── .gitignore              # committed FIRST, before any secret file exists
├── .env.example            # template, committed
├── .env                    # gitignored, real secrets
├── credentials.json        # gitignored, Google OAuth client
├── token.json              # gitignored, auto-generated on first Google call
├── requirements.txt
├── README.md               # PRD + setup walkthrough
├── agent.py                # entry point: system prompt + Strands agent loop
├── test_model.py           # validation gate 1: model connectivity only
└── tools/
    ├── __init__.py         # re-exports check_gmail, check_calendar, check_slack
    ├── gmail.py            # @tool check_gmail + standalone __main__ smoke test
    ├── calendar.py         # @tool check_calendar + standalone __main__
    └── slack.py            # @tool check_slack + standalone __main__
```

Rationale for modular `tools/`: the PRD's validation plan requires each tool to be independently runnable with real data before the agent runs end-to-end. One file per tool keeps that boundary clean and prevents `agent.py` from accumulating three integrations' worth of helper code.

## Dependencies

Pinned in `requirements.txt`:

- `strands-agents` — agent framework, owns the tool-call loop.
- `litellm` — adapter between Strands and OpenRouter's API format.
- `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2` — Gmail + Calendar.
- `slack-sdk` — Slack Web API client.
- `python-dotenv` — load `.env` into environment.

Setup: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`. Python 3.10+ required (modern type-hint syntax).

## Module Interfaces

```python
# tools/gmail.py
@tool
def check_gmail(hours_back: int = 12) -> list[dict]:
    """Returns unread emails from the last `hours_back` hours.

    Each dict: {sender, subject, date, snippet}  (snippet ≤ 200 chars)
    """

# tools/calendar.py
@tool
def check_calendar(hours_ahead: int = 24) -> list[dict]:
    """Returns calendar events starting in the next `hours_ahead` hours.

    Each dict: {title, start, end, location, attendees}  (times in system local TZ)
    """

# tools/slack.py
@tool
def check_slack(hours_back: int = 12, max_channels: int = 5) -> list[dict]:
    """Returns recent activity from up to `max_channels` most-recently-active channels.

    Each dict: {channel, messages: [{user, ts, text}, ...]}  (≤ 5 messages each)
    """
```

Each tool file also exposes an `if __name__ == "__main__":` block that prints the tool's output as JSON, so `python -m tools.gmail` works as a standalone smoke test.

## Agent Configuration

`agent.py`:

- Loads `.env` via `dotenv`.
- Constructs `LiteLLMModel` with `model_id="openrouter/openrouter/free"` and `params={"max_tokens": 4096}`. The `max_tokens` value sits inside `params={}`, not at the top level — top-level placement is rejected by LiteLLM, and 2048 is too low for three tool results in context.
- Builds a Strands `Agent` with all three tool functions registered and the system prompt below.
- Runs once with the goal prompt `"What did I miss? Give me my morning briefing."` and prints the synthesized result to stdout.

System prompt (working draft, refined during implementation):

> You are a personal morning briefing assistant. Call all three tools — `check_gmail`, `check_calendar`, `check_slack` — in order, then synthesize the results into a single briefing with exactly these five sections, in this order: URGENT, UPCOMING EVENTS, SLACK HIGHLIGHTS, OTHER EMAILS, SUGGESTED ACTIONS. Be concise. If a section has nothing, write "(none)".

## Build Order

Each step is a verification gate for the next.

1. **Scaffold** — write `.gitignore` first, then `requirements.txt`, `.env.example`, empty module files; create venv; install dependencies.
2. **OpenRouter** — walkthrough to obtain `OPENROUTER_API_KEY` and put it in `.env`. Verify with `python test_model.py` (returns a one-sentence greeting).
3. **Google Cloud** — walkthrough: enable Gmail API + Calendar API, create OAuth client (Desktop app), download `credentials.json` to project root. Verify Gmail with `python -m tools.gmail` (prints unread email list, triggers OAuth consent on first run, writes `token.json`).
4. **Calendar** — no new setup; reuses Google credentials from step 3. Verify with `python -m tools.calendar`.
5. **Slack** — walkthrough: create Slack app at `api.slack.com/apps`, add four User Token Scopes (`channels:read`, `channels:history`, `groups:read`, `groups:history`), install to workspace, copy User OAuth Token into `.env` as `SLACK_BOT_TOKEN`. Verify with `python -m tools.slack`.
6. **Wire it up** — `agent.py` registers all three tools and prints a five-section briefing.

## Implementation-Level Choices

These are the choices the PRD leaves open. None are load-bearing enough to need a separate decision pass; recording them so future-me can see what was assumed.

- **Python version:** 3.10+ (modern type-hint syntax).
- **Calendar timezone:** system local timezone, formatted human-readably (e.g., `"2026-05-03 14:00 PDT"`).
- **Gmail filter:** `in:inbox is:unread newer_than:{hours_back}h`.
- **Slack channel scope:** `conversations.list` with `types="public_channel,private_channel"`, filtered to channels the user is a member of (`is_member=True` for public; private channels are member-only by API).
- **Slack channel ranking:** sort the candidate channels by most-recent message timestamp within the window, descending; take top `max_channels`. Pull last 5 messages per channel via `conversations.history` with `limit=5`.
- **Slack user names:** resolve user IDs to display names via `users.info`, cached in-memory per run.
- **Error handling:** tools return `[]` on auth failure or API error and log the error to stderr. The agent will see an empty list and synthesize accordingly. Crashing the run on a single tool failure is worse than degrading gracefully — one of the three sources is still better than none.

## Security

- `.gitignore` contains `.env`, `token.json`, `credentials.json`, `.venv/`, `__pycache__/`, `*.pyc` and is committed before any secret file exists on disk.
- Google scopes: `gmail.readonly`, `calendar.readonly`. No write scopes ever requested.
- Slack scopes: `channels:read`, `channels:history`, `groups:read`, `groups:history` (all read-only) under User Token Scopes — Bot Token Scopes are explicitly wrong here per the PRD's failure modes table.
- The Slack user token carries my full identity. This is acceptable only because the agent runs on my laptop. The PRD's warning ("Never use this pattern in shared or production code") is repeated in the README setup walkthrough.
- If anything leaks: revoke the OpenRouter key in their dashboard, revoke the Google OAuth client and delete `token.json`, reinstall the Slack app to invalidate the user token. Regenerate.

## Validation Plan

Mirrors the PRD section. Each gate must pass before proceeding to the next:

1. `python test_model.py` returns a one-sentence greeting → model connectivity confirmed.
2. `python -m tools.gmail`, `python -m tools.calendar`, `python -m tools.slack` each print real data → tools work in isolation.
3. `python agent.py` produces a briefing with all five sections populated from real data → end-to-end success.

## Future Extensions (deferred)

Captured in PRD; not part of this build. Each is a tool change or prompt change, nothing structural:

- VIP sender list and urgency keyword matching in the system prompt.
- Marketing-domain noise filter inside `check_gmail`.
- Additional sources (GitHub, Linear, Notion) as new `@tool`-decorated functions.
- Scheduled run via `cron` or `launchd`.
- Slack DM delivery instead of stdout.
