"""FastAPI app: sessions, resume upload, chat, and the application tracker."""

from __future__ import annotations

import uuid
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import asdict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import skills
from .agent import Agent
from .config import get_settings
from .llm import GeminiClient, LLMClient, LLMError
from .resume import ResumeError, extract_text
from .tools import ToolContext
from .tracker import STATUSES, Tracker

MAX_SESSIONS = 200


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)


class ApplicationPatch(BaseModel):
    status: str | None = None
    notes: str | None = None
    cover_letter: str | None = None


def create_app(llm_factory: Callable[[], LLMClient] | None = None, db_path: str | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="JobFit Agent", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    tracker = Tracker(db_path or settings.database_path)
    make_llm = llm_factory or (lambda: GeminiClient(settings.gemini_api_key, settings.gemini_model))
    # In-memory sessions (one agent + resume per browser tab). Oldest are evicted first.
    sessions: OrderedDict[str, Agent] = OrderedDict()

    def get_session(session_id: str) -> Agent:
        agent = sessions.get(session_id)
        if agent is None:
            raise HTTPException(404, "Session not found or expired. Refresh the page to start a new one.")
        sessions.move_to_end(session_id)
        return agent

    # ---------- routes ----------
    @app.get("/api/health")
    def health():
        return {"status": "ok", "model": settings.gemini_model, "api_key_set": bool(settings.gemini_api_key)}

    @app.post("/api/sessions")
    def create_session():
        try:
            llm = make_llm()
        except LLMError as exc:
            raise HTTPException(503, str(exc)) from exc
        session_id = uuid.uuid4().hex
        sessions[session_id] = Agent(llm, ToolContext(tracker=tracker), max_steps=settings.max_agent_steps)
        while len(sessions) > MAX_SESSIONS:
            sessions.popitem(last=False)
        return {"session_id": session_id}

    @app.post("/api/sessions/{session_id}/resume")
    async def upload_resume(session_id: str, file: UploadFile = File(...)):
        agent = get_session(session_id)
        try:
            text = extract_text(file.filename or "", await file.read())
        except ResumeError as exc:
            raise HTTPException(400, str(exc)) from exc
        agent.ctx.resume_text = text
        return {
            "filename": file.filename,
            "characters": len(text),
            "skills": skills.extract_skills(text),
            "preview": text[:600],
        }

    @app.post("/api/sessions/{session_id}/chat")
    def chat(session_id: str, body: ChatIn):
        agent = get_session(session_id)
        try:
            reply = agent.chat(body.message)
        except LLMError as exc:
            raise HTTPException(502, str(exc)) from exc
        return {
            "reply": reply.text,
            "trace": [asdict(step) for step in reply.trace],
            "stopped_early": reply.stopped_early,
        }

    @app.get("/api/applications")
    def list_applications(status: str | None = None):
        return {"applications": tracker.list(status), "statuses": list(STATUSES)}

    @app.patch("/api/applications/{app_id}")
    def update_application(app_id: int, body: ApplicationPatch):
        try:
            return tracker.update(app_id, **body.model_dump())
        except KeyError as exc:
            raise HTTPException(404, "Application not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.delete("/api/applications/{app_id}")
    def delete_application(app_id: int):
        if not tracker.delete(app_id):
            raise HTTPException(404, "Application not found")
        return {"deleted": True}

    return app


app = create_app()
