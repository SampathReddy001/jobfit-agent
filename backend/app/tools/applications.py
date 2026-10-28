"""Tools that read and write the application tracker."""

from __future__ import annotations

from ..tracker import STATUSES
from .registry import ToolContext, tool


@tool(
    name="save_application",
    description=(
        "Add a job to the user's application tracker. Only call this when the user asks to save or track a job."
    ),
    parameters={
        "type": "object",
        "properties": {
            "company": {"type": "string"},
            "role": {"type": "string"},
            "job_url": {"type": "string"},
            "fit_score": {"type": "integer", "description": "Score from match_skills"},
            "status": {"type": "string", "enum": list(STATUSES)},
            "notes": {"type": "string", "description": "Short notes, e.g. key gaps to work on"},
        },
        "required": ["company", "role"],
    },
)
def save_application(ctx: ToolContext, company: str, role: str, **kwargs) -> dict:
    key = (company.strip().lower(), role.strip().lower())
    for existing in ctx.tracker.list():
        if (existing["company"].lower(), existing["role"].lower()) == key:
            existing.pop("cover_letter", None)
            return {
                "already_tracked": existing,
                "note": "This job is already in the tracker; use update_application to change it.",
            }
    try:
        return {"saved": ctx.tracker.add(company=company, role=role, **kwargs)}
    except ValueError as exc:
        return {"error": str(exc)}


@tool(
    name="list_applications",
    description="List tracked job applications, optionally filtered by status.",
    parameters={
        "type": "object",
        "properties": {"status": {"type": "string", "enum": list(STATUSES)}},
    },
)
def list_applications(ctx: ToolContext, status: str | None = None) -> dict:
    apps = ctx.tracker.list(status)
    # Cover letters can be long; the model only needs to know one exists.
    for a in apps:
        a["has_cover_letter"] = bool(a.pop("cover_letter", None))
    return {"applications": apps, "count": len(apps)}


@tool(
    name="update_application",
    description="Change the status or notes of a tracked application.",
    parameters={
        "type": "object",
        "properties": {
            "application_id": {"type": "integer"},
            "status": {"type": "string", "enum": list(STATUSES)},
            "notes": {"type": "string"},
        },
        "required": ["application_id"],
    },
)
def update_application(
    ctx: ToolContext, application_id: int, status: str | None = None, notes: str | None = None
) -> dict:
    try:
        app = ctx.tracker.update(int(application_id), status=status, notes=notes)
    except (KeyError, ValueError) as exc:
        return {"error": str(exc).strip("'\"")}
    app.pop("cover_letter", None)
    return {"updated": app}


@tool(
    name="save_cover_letter",
    description="Attach a cover letter you drafted to a tracked application, after the user approves it.",
    parameters={
        "type": "object",
        "properties": {
            "application_id": {"type": "integer"},
            "cover_letter": {"type": "string"},
        },
        "required": ["application_id", "cover_letter"],
    },
)
def save_cover_letter(ctx: ToolContext, application_id: int, cover_letter: str) -> dict:
    try:
        ctx.tracker.update(int(application_id), cover_letter=cover_letter)
    except KeyError as exc:
        return {"error": str(exc).strip("'\"")}
    return {"saved": True, "application_id": int(application_id)}
