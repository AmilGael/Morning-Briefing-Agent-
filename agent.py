"""Morning Briefing Agent — entry point.

Runs the Strands agent loop with three read-only tools and prints a
five-section briefing.
"""
import sys
from typing import Any

from dotenv import load_dotenv
from strands import Agent
from strands.models.litellm import LiteLLMModel

from tools import check_calendar, check_gmail, check_slack

load_dotenv()


def _progress_callback(**kwargs: Any) -> None:
    """Minimal progress indicator on stderr.

    Strands' default PrintingCallbackHandler streams reasoning + answer to
    stdout, which contaminates the briefing output. We want stdout to be
    briefing-only, but a fully silent agent run leaves the user wondering
    if the process is hung. Compromise: print a one-line marker to stderr
    when each tool fires. Three lines on the busy side is enough signal.
    """
    tool_use = (
        kwargs.get("event", {})
        .get("contentBlockStart", {})
        .get("start", {})
        .get("toolUse")
    )
    if tool_use:
        print(f"→ {tool_use['name']}", file=sys.stderr, flush=True)


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
    print("→ starting agent (model + 3 tools, can take 60-180s)", file=sys.stderr, flush=True)
    model = LiteLLMModel(
        model_id="openrouter/openrouter/free",
        params={"max_tokens": 4096},
    )
    agent = Agent(
        model=model,
        tools=[check_gmail, check_calendar, check_slack],
        system_prompt=SYSTEM_PROMPT,
        callback_handler=_progress_callback,
    )
    result = agent("What did I miss? Give me my morning briefing.")
    print("→ synthesized", file=sys.stderr, flush=True)

    # AgentResult.__str__ concatenates every text content block in the final
    # message. Some routed free models emit reasoning + answer as two separate
    # text blocks, which produces a duplicated briefing if we print all of them.
    # Take the last text block — it's the final answer for both well-behaved
    # single-block models and split-block models.
    texts = [
        block["text"]
        for block in result.message.get("content", [])
        if "text" in block
    ]
    print(texts[-1] if texts else "")


if __name__ == "__main__":
    main()
