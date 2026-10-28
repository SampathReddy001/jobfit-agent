import os

# Must be set before the app module is imported.
os.environ.setdefault("DATABASE_PATH", ":memory:")
os.environ.setdefault("GEMINI_API_KEY", "")

from collections.abc import Callable  # noqa: E402
from typing import Any

import pytest  # noqa: E402

from app.llm import ModelTurn, ToolCall  # noqa: E402
from app.tools import ToolContext  # noqa: E402
from app.tracker import Tracker  # noqa: E402

SAMPLE_RESUME = """\
Sampath Reddy
Full-stack developer

Skills: Python, JavaScript, React, Node.js, Express, MongoDB, FastAPI, Docker, pandas, TensorFlow, Git

Projects
- ShopHub: e-commerce platform with React, Node.js, Express and MongoDB, JWT auth, Docker Compose.
- Olist analysis: pandas and Seaborn analysis of 96K orders with RFM segmentation.
"""

SAMPLE_JOB = """\
Junior AI Engineer - Acme Corp

Requirements
- Strong Python and SQL
- Experience with React and REST APIs
- Familiarity with LLMs and Docker

Nice to have
- Kubernetes
- PyTorch
"""


class FakeLLM:
    """A scripted stand-in for Gemini. Each script item is a ModelTurn or a
    function(history) -> ModelTurn, returned in order on each generate() call."""

    def __init__(self, script: list[ModelTurn | Callable[[list[Any]], ModelTurn]]):
        self.script = list(script)
        self.calls: list[list[Any]] = []

    def user_message(self, text: str) -> Any:
        return {"role": "user", "text": text}

    def tool_results_message(self, results):
        return {"role": "tool", "results": results}

    def generate(self, history, tools, system) -> ModelTurn:
        self.calls.append(list(history))
        assert tools and system
        step = self.script.pop(0)
        turn = step(history) if callable(step) else step
        turn.raw = {"role": "model", "text": turn.text, "calls": [c.name for c in turn.tool_calls]}
        return turn


def call(name: str, **args) -> ToolCall:
    return ToolCall(name=name, args=args)


def last_tool_result(history, tool_name: str) -> dict:
    for msg in reversed(history):
        if msg.get("role") == "tool":
            for name, result in msg["results"]:
                if name == tool_name:
                    return result
    raise AssertionError(f"no result for {tool_name}")


@pytest.fixture
def ctx() -> ToolContext:
    return ToolContext(tracker=Tracker(":memory:"), resume_text=SAMPLE_RESUME)
