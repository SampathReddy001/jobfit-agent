"""A thin wrapper around the Gemini API.

The agent loop talks to the model only through the small `LLMClient` interface
below. That keeps the loop independent of any one provider and lets the tests
swap in a scripted fake model, so they run without an API key or network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass
class ModelTurn:
    """One response from the model: either tool calls, final text, or both."""

    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    # The provider's own message object, appended to history as-is so that
    # provider metadata (e.g. Gemini thought signatures) is preserved.
    raw: Any = None


class LLMError(RuntimeError):
    """Raised when the model provider fails (bad key, quota, network...)."""


class LLMClient(Protocol):
    def user_message(self, text: str) -> Any: ...

    def tool_results_message(self, results: list[tuple[str, dict[str, Any]]]) -> Any: ...

    def generate(self, history: list[Any], tools: list[dict[str, Any]], system: str) -> ModelTurn: ...


class GeminiClient:
    """`LLMClient` implementation backed by the google-genai SDK."""

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LLMError(
                "GEMINI_API_KEY is not set. Create one at https://aistudio.google.com/apikey and add it to backend/.env"
            )
        from google import genai  # imported lazily so tests don't need it

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def user_message(self, text: str) -> Any:
        from google.genai import types

        return types.Content(role="user", parts=[types.Part.from_text(text=text)])

    def tool_results_message(self, results: list[tuple[str, dict[str, Any]]]) -> Any:
        from google.genai import types

        parts = [types.Part.from_function_response(name=name, response=resp) for name, resp in results]
        return types.Content(role="tool", parts=parts)

    def generate(self, history: list[Any], tools: list[dict[str, Any]], system: str) -> ModelTurn:
        from google.genai import errors, types

        declarations = [
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters_json_schema=t["parameters"],
            )
            for t in tools
        ]
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=declarations)],
            # We run the tool loop ourselves (see agent.py) so every step is visible.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.4,
        )
        try:
            response = self._client.models.generate_content(model=self._model, contents=history, config=config)
        except errors.APIError as exc:
            raise LLMError(f"Gemini API error ({exc.code}): {exc.message}") from exc
        except Exception as exc:  # network errors and the like
            raise LLMError(f"Could not reach Gemini: {exc}") from exc

        if not response.candidates or response.candidates[0].content is None:
            raise LLMError("Gemini returned an empty response (it may have been blocked by safety filters).")

        calls = [ToolCall(name=c.name, args=dict(c.args or {})) for c in (response.function_calls or [])]
        text_parts = [
            p.text
            for p in (response.candidates[0].content.parts or [])
            if getattr(p, "text", None) and not getattr(p, "thought", False)
        ]
        return ModelTurn(
            text="".join(text_parts) or None,
            tool_calls=calls,
            raw=response.candidates[0].content,
        )
