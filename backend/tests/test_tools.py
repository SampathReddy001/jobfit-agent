from app.agent import run_tool
from app.tools.job_posting import _is_public_url, html_to_text
from conftest import SAMPLE_JOB


def test_html_to_text_strips_scripts_and_nav():
    html = """<html><head><title>Data Analyst</title><script>var x=1</script></head>
    <body><nav>Home | Jobs</nav><main><h1>Data Analyst</h1><p>Use SQL daily.</p></main></body></html>"""
    title, text = html_to_text(html)
    assert title == "Data Analyst"
    assert "Use SQL daily." in text
    assert "var x" not in text and "Home | Jobs" not in text


def test_private_urls_are_blocked():
    assert not _is_public_url("http://localhost:8000/admin")
    assert not _is_public_url("http://127.0.0.1/")
    assert not _is_public_url("http://192.168.1.10/")
    assert not _is_public_url("file:///etc/passwd")


def test_fetch_job_posting_refuses_private_url(ctx):
    result = run_tool(ctx, "fetch_job_posting", {"url": "http://127.0.0.1/secret"})
    assert "error" in result


def test_save_job_then_match(ctx):
    saved = run_tool(ctx, "save_job_description", {"description": SAMPLE_JOB, "company": "Acme", "title": "AI Eng"})
    assert "text" not in saved
    result = run_tool(ctx, "match_skills", {"job_id": saved["job_id"]})
    assert result["fit_score"] == 43
    assert "SQL" in result["missing_required"]


def test_match_requires_resume(ctx):
    ctx.resume_text = None
    saved = run_tool(ctx, "save_job_description", {"description": SAMPLE_JOB})
    assert "error" in run_tool(ctx, "match_skills", {"job_id": saved["job_id"]})


def test_learning_resources_curated_and_fallback(ctx):
    result = run_tool(ctx, "find_learning_resources", {"skills": ["sql", "Underwater Basket Weaving"]})["resources"]
    assert result["sql"][0]["url"].startswith("https://sqlbolt.com")
    assert "youtube.com" in result["Underwater Basket Weaving"][0]["url"]


def test_tracker_tools_round_trip(ctx):
    saved = run_tool(ctx, "save_application", {"company": "Acme", "role": "AI Eng", "fit_score": 43})["saved"]
    run_tool(ctx, "update_application", {"application_id": saved["id"], "status": "applied"})
    run_tool(ctx, "save_cover_letter", {"application_id": saved["id"], "cover_letter": "Dear Acme..."})
    listed = run_tool(ctx, "list_applications", {})
    assert listed["count"] == 1
    app = listed["applications"][0]
    assert app["status"] == "applied" and app["has_cover_letter"] is True


def test_bad_status_returns_error_not_exception(ctx):
    result = run_tool(ctx, "save_application", {"company": "Acme", "role": "Dev", "status": "ghosted"})
    assert "error" in result


def test_unknown_tool_and_extra_args(ctx):
    assert "error" in run_tool(ctx, "launch_rockets", {})
    # Unknown extra arguments are dropped instead of crashing the tool.
    assert "resume_text" in run_tool(ctx, "get_resume", {"verbose": True})


def test_save_application_does_not_duplicate(ctx):
    run_tool(ctx, "save_application", {"company": "Acme", "role": "AI Eng"})
    again = run_tool(ctx, "save_application", {"company": " acme ", "role": "ai eng"})
    assert "already_tracked" in again
    assert run_tool(ctx, "list_applications", {})["count"] == 1
