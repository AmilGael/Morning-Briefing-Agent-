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
3. Configure the **OAuth consent screen** as **External**, and add your own Gmail address as a **test user** (otherwise the OAuth flow will block with "Access blocked: app has not completed Google verification").
4. Create an **OAuth client ID** of type **Desktop app**. Download the JSON, rename it to `credentials.json`, and put it in the project root.

Verify: `python -m tools.gmail` opens a browser for consent the first time, then prints unread mail. `python -m tools.calendar` should also work without a second consent prompt.

### 4. Slack

1. Create a new app at <https://api.slack.com/apps> → **From scratch**.
2. Under **OAuth & Permissions**, scroll to **User Token Scopes** (NOT Bot Token Scopes — Bot scopes won't see your channel history). Add: `channels:read`, `channels:history`, `groups:read`, `groups:history`.
3. **Install to Workspace** and copy the **User OAuth Token** (starts with `xoxp-`).
4. Paste into `.env` as `SLACK_BOT_TOKEN=xoxp-...`. The env var name is `SLACK_BOT_TOKEN` even though the value is a user token — kept this way for compatibility with the original PRD.

Verify: `python -m tools.slack` prints recent activity from your top channels.

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
- All API scopes are read-only (Gmail/Calendar `*.readonly`, Slack `*:read` / `*:history`).
- Slack uses a **user token** that carries your full identity. This is acceptable only because the agent runs on your laptop. **Never use this pattern in shared or production code.**
- If anything leaks: revoke the OpenRouter key, revoke the Google OAuth client (and delete `token.json`), reinstall the Slack app to invalidate the user token. Regenerate.

## Troubleshooting

- **"Access blocked: app has not completed Google verification"** — you forgot to add yourself as a test user in step 3 (OAuth consent screen → Test users).
- **`invalid_auth` or `missing_scope` from Slack** — you added Bot Token Scopes instead of User Token Scopes. Re-add under User Token Scopes, reinstall the app, copy the new `xoxp-` token.
- **`MaxTokensReachedException`** — the routed free model produced very verbose reasoning and ran out. Re-run; it's usually intermittent.
- **`429 Too Many Requests`** — OpenRouter free-tier rate limit. Wait 60 seconds and retry.

## Original design docs

- Spec: `docs/superpowers/specs/2026-05-03-morning-briefing-agent-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-03-morning-briefing-agent.md`
