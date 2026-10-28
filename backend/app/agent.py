"""The agent loop.

    user message
        -> model decides: answer, or call one or more tools
        -> we run the tools and send results back
        -> repeat until the model answers (or we hit max_steps)

Every tool call is recorded in a `trace` so the UI can show exactly what the
agent did and why its answer can be trusted.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .llm import LLMClient
from .tools import ToolContext, all_tools, get_tool

SYSTEM_PROMPT = """\
You are JobFit, a friendly, practical job-hunt assistant for students and early-career developers.

You have tools. Use them instead of guessing:
- get_resume: read the user's uploaded resume.
- fetch_job_posting (URL) or save_job_description (pasted text): load a job. Both return a job_id.
- match_skills(job_id): get the fit score and matched / missing skills. Never invent a score.
- find_learning_resources: free resources for missing skills.
- save_application, list_applications, update_application, save_cover_letter: the user's tracker.

How to analyze a job:
1. Load the resume and the job.
2. Call match_skills.
3. Reply with: the fit score, top strengths (matched skills backed by resume evidence),
   the most important gaps, and 2-3 concrete next steps. Offer learning resources for the
   biggest gaps and offer to save the job to the tracker or draft a cover letter.

Cover letters:
- Use ONLY experience, projects, and skills that appear in the resume. Never invent
  employers, degrees, numbers, or skills. If something important is missing, say so.
- Tailor to the job's actual requirements, 250-350 words, confident and specific, no clichés.
- Only call save_cover_letter after the user approves the draft.

Write the tracker only when the user asks (e.g. "save this", "mark it applied").
Be concise. Use short headings and bullet points in Markdown.
"""


@dataclass
class TraceStep:
    tool: str
    args: dict[str, Any]
    result: dict[str, Any]
    ok: bool
    duration_ms: int


@dataclass
class AgentReply:
    text: str
    trace: list[TraceStep] = field(default_factory=list)
    stopped_early: bool = False


def _clean_args(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Drop any arguments the tool doesn't declare (models occasionally add extras)."""
    t = get_tool(tool_name)
    allowed = set(t.parameters.get("properties", {})) if t else set()
    return {k: v for k, v in args.items() if k in allowed}


def run_tool(ctx: ToolContext, name: str, args: dict[str, Any]) -> dict[str, Any]:
    t = get_tool(name)
    if t is None:
        return {"error": f"Unknown tool '{name}'."}
    try:
        return t.func(ctx, **_clean_args(name, args))
    except TypeError as exc:  # missing / wrong arguments
        return {"error": f"Bad arguments for {name}: {exc}"}
    except Exception as exc:  # a tool bug should not crash the conversation
        return {"error": f"{name} failed: {exc}"}


def _summarize_for_trace(result: dict[str, Any]) -> dict[str, Any]:
    """Keep the trace readable: truncate long strings such as page text."""
    out = {}
    for k, v in result.items():
        if isinstance(v, str) and len(v) > 400:
            out[k] = v[:400] + f"… ({len(v):,} chars)"
        else:
            out[k] = v
    return out


class Agent:
    def __init__(self, llm: LLMClient, ctx: ToolContext, max_steps: int = 8):
        self.llm = llm
        self.ctx = ctx
        self.max_steps = max_steps
        self.history: list[Any] = []

    def chat(self, message: str) -> AgentReply:
        start = len(self.history)
        try:
            return self._run(message)
        except Exception:
            # Roll back this whole exchange so a failed request (quota, network)
            # never leaves the history in a half-finished state.
            del self.history[start:]
            raise

    def _run(self, message: str) -> AgentReply:
        self.history.append(self.llm.user_message(message))
        schemas = [t.schema() for t in all_tools()]
        trace: list[TraceStep] = []

        for _ in range(self.max_steps):
            turn = self.llm.generate(self.history, schemas, SYSTEM_PROMPT)
            self.history.append(turn.raw)

            if not turn.tool_calls:
                return AgentReply(text=turn.text or "", trace=trace)

            results = []
            for call in turn.tool_calls:
                start = time.perf_counter()
                result = run_tool(self.ctx, call.name, call.args)
                trace.append(
                    TraceStep(
                        tool=call.name,
                        args=call.args,
                        result=_summarize_for_trace(result),
                        ok="error" not in result,
                        duration_ms=round((time.perf_counter() - start) * 1000),
                    )
                )
                results.append((call.name, result))
            self.history.append(self.llm.tool_results_message(results))

        return AgentReply(
            text="I hit my step limit before finishing. Could you narrow the request down a little?",
            trace=trace,
            stopped_early=True,
        )
