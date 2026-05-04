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
