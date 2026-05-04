Morning Briefing Agent — PRD

TL;DR
A single-command CLI agent that reads my Gmail, Calendar, and Slack, then prints one prioritized morning briefing. Personal tool, runs locally, free LLM via OpenRouter.
Problem
Three inboxes every morning, no synthesis. I open Gmail, scan Calendar, scroll Slack, and end up holding the prioritization in my head. I want one read instead of three.
Goals

One command (python agent.py) produces one synthesized briefing
Real data from Gmail, Calendar, Slack (not mocks)
Free model tier, no credit card
Reproducible setup from a clean clone in under 30 minutes

Non-Goals

Not deployed, not multi-user, not a service
No write actions (no replies, no event creation, no Slack posts)
No real-time or push delivery
No GUI

User
Me. Personal laptop. Existing Gmail, Calendar, Slack accounts I already use.
Stack
ComponentRoleStrandsAgent framework. Runs the tool-call loop and feeds results back to the model.LiteLLMAdapter between Strands and OpenRouter's API format.OpenRouterLLM gateway. Routes to free open-source models.openrouter/openrouter/freeModel ID. Auto-selects a free model that supports tool calling.Python toolscheck_gmail, check_calendar, check_slack. The agent's hands.
Agent Loop
goal = "What did I miss? Give me my morning briefing."
system_prompt = "Call all three tools in order, then synthesize."

while not done:
    next_action = model.decide(history)
    if next_action is tool_call:
        result = run_tool(next_action)
        history.append(result)
    else:
        return synthesize(history)
The loop is owned by Strands. I own the tool definitions and the system prompt.
Tools
ToolArgsReturnscheck_gmailhours_back=12List of unread emails: sender, subject, date, 200-char snippetcheck_calendarhours_ahead=24List of events: title, start, end, location, attendeescheck_slackhours_back=12, max_channels=5Top 5 most recently active channels, up to 5 messages each
All three are read-only. All three return structured data the model can reason over.
Output Format
Five fixed sections, in this order:

URGENT
UPCOMING EVENTS
SLACK HIGHLIGHTS
OTHER EMAILS
SUGGESTED ACTIONS

The system prompt enforces this structure. The model fills it in.
Setup Dependencies
ItemSourceStored InOpenRouter API keyopenrouter.ai.env → OPENROUTER_API_KEYGoogle OAuth clientconsole.cloud.google.comcredentials.json (project root)Google access tokenAuto-generated on first runtoken.json (project root)Slack user tokenapi.slack.com/apps.env → SLACK_BOT_TOKEN
Google scopes: gmail.readonly, calendar.readonly
Slack scopes (User Token Scopes, not Bot): channels:read, channels:history, groups:read, groups:history
Security

All secrets in .env. .env, token.json, credentials.json in .gitignore before any git init.
Slack uses a user token, which carries my full identity. Acceptable because this runs on my laptop only. Never use this pattern in shared or production code.
All API scopes are read-only.
If anything leaks, revoke and regenerate immediately.

Model Config Decisions
DecisionChoiceWhymodel_idopenrouter/openrouter/freeAuto-routes to free models that support tool calling. Specific models like Llama or Gemma may or may not be available on the free tier.max_tokens4096, inside params={}2048 triggers MaxTokensReachedException once all three tool results are in context. Top-level max_tokens is rejected by LiteLLM.Provider classLiteLLMStrands needs LiteLLM as the adapter to talk to OpenRouter.
Known Failure Modes
SymptomCauseFixNo endpoints found that support tool useModel doesn't support tool callingUse openrouter/openrouter/free429 Too Many RequestsFree tier rate limitWait 1 minute, retryInvalid configuration parameters: ['max_tokens']max_tokens set top-levelMove into params={"max_tokens": 4096}MaxTokensReachedException2048 too low for three tool resultsSet max_tokens to 4096Got unexpected keyword argument messageIdGoogle API uses id=, not messageId=Rename param in messages().get()Missing credentials.jsonFile not in project rootDownload from Google Cloud Console, rename, moveSlack returns no channelsUsed Bot Token Scopes instead of User Token ScopesRe-add scopes under User Token Scopes, reinstall app
Validation Plan

Model connectivity: test_model.py returns a one-sentence greeting before any tools are wired in.
Tool isolation: Each tool callable from a one-liner with real data before the agent runs end-to-end.
Full run: python agent.py produces a briefing with all five sections populated from real Gmail, Calendar, and Slack data.

Future Extensions
Each one is a tool change or a prompt change, nothing structural:

Urgency rules: VIP sender list + subject keyword match (urgent, deadline, action required) injected into the system prompt
Noise filter: Drop marketing domains in check_gmail before results reach the model
More sources: GitHub notifications, Linear issues, Notion mentions as additional @tool-decorated functions
Scheduled run: cron or launchd at 7am
Delivery channel: DM the briefing to myself in Slack instead of stdout
