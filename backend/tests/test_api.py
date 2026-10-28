import io

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.llm import LLMError, ModelTurn
from app.main import create_app
from conftest import SAMPLE_RESUME, FakeLLM, call


def make_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in text.splitlines():
        c.drawString(40, y, line)
        y -= 14
    c.save()
    return buf.getvalue()


@pytest.fixture
def fake():
    return FakeLLM([])


@pytest.fixture
def client(fake):
    return TestClient(create_app(llm_factory=lambda: fake, db_path=":memory:"))


@pytest.fixture
def session(client):
    return client.post("/api/sessions").json()["session_id"]


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_resume_upload_pdf(client, session):
    files = {"file": ("resume.pdf", make_pdf(SAMPLE_RESUME), "application/pdf")}
    body = client.post(f"/api/sessions/{session}/resume", files=files).json()
    assert {"Python", "React", "MongoDB", "Docker"} <= set(body["skills"])


def test_resume_rejects_unsupported_type(client, session):
    files = {"file": ("resume.exe", b"MZ" * 100, "application/octet-stream")}
    assert client.post(f"/api/sessions/{session}/resume", files=files).status_code == 400


def test_chat_returns_reply_and_trace(client, session, fake):
    client.post(f"/api/sessions/{session}/resume", files={"file": ("r.txt", SAMPLE_RESUME.encode(), "text/plain")})
    fake.script = [
        ModelTurn(text=None, tool_calls=[call("save_application", company="Acme", role="AI Engineer", fit_score=43)]),
        ModelTurn(text="Saved Acme to your tracker."),
    ]
    body = client.post(f"/api/sessions/{session}/chat", json={"message": "save Acme"}).json()
    assert body["reply"] == "Saved Acme to your tracker."
    assert body["trace"][0]["tool"] == "save_application"

    apps = client.get("/api/applications").json()["applications"]
    assert apps[0]["company"] == "Acme"

    patched = client.patch(f"/api/applications/{apps[0]['id']}", json={"status": "interviewing"}).json()
    assert patched["status"] == "interviewing"
    assert client.patch(f"/api/applications/{apps[0]['id']}", json={"status": "bogus"}).status_code == 400
    assert client.delete(f"/api/applications/{apps[0]['id']}").json() == {"deleted": True}
    assert client.delete(f"/api/applications/{apps[0]['id']}").status_code == 404


def test_llm_failure_returns_502_and_keeps_history_valid(client, session, fake):
    def boom(history):
        raise LLMError("quota exceeded")

    fake.script = [boom]
    resp = client.post(f"/api/sessions/{session}/chat", json={"message": "hi"})
    assert resp.status_code == 502 and "quota" in resp.json()["detail"]

    # The failed exchange was rolled back, so the next message starts clean.
    fake.script = [ModelTurn(text="Hello again!")]
    assert client.post(f"/api/sessions/{session}/chat", json={"message": "hi"}).json()["reply"] == "Hello again!"
    assert fake.calls[-1] == [{"role": "user", "text": "hi"}]


def test_unknown_session(client):
    assert client.post("/api/sessions/nope/chat", json={"message": "hi"}).status_code == 404


def test_missing_api_key_gives_clear_error():
    from app.llm import GeminiClient

    app = create_app(llm_factory=lambda: GeminiClient(api_key="", model="x"), db_path=":memory:")
    resp = TestClient(app).post("/api/sessions")
    assert resp.status_code == 503 and "GEMINI_API_KEY" in resp.json()["detail"]
