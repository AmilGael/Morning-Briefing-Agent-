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
