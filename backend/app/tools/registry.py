"""A tiny tool registry.

Each tool is a plain Python function plus a JSON schema describing its
arguments. The schema is what the model sees; the function is what runs when
the model asks for it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..tracker import Tracker


@dataclass
class ToolContext:
    """Per-session state that tools can read and write."""

    tracker: Tracker
    resume_text: str | None = None
    # Job postings the agent has loaded this session, keyed by a short id.
    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., dict[str, Any]]

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


_REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, parameters: dict[str, Any]):
    """Decorator that registers a function as a tool the agent can call."""

    def wrap(func: Callable[..., dict[str, Any]]):
        _REGISTRY[name] = Tool(name=name, description=description, parameters=parameters, func=func)
        return func

    return wrap


def all_tools() -> list[Tool]:
    return list(_REGISTRY.values())


def get_tool(name: str) -> Tool | None:
    return _REGISTRY.get(name)
