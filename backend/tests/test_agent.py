from app.agent import Agent
from app.llm import ModelTurn
from conftest import SAMPLE_JOB, FakeLLM, call, last_tool_result


def test_agent_runs_multi_step_tool_loop(ctx):
    llm = FakeLLM(
        [
            ModelTurn(text=None, tool_calls=[call("get_resume"), call("save_job_description", description=SAMPLE_JOB)]),
            lambda h: ModelTurn(
                text=None,
                tool_calls=[call("match_skills", job_id=last_tool_result(h, "save_job_description")["job_id"])],
            ),
            lambda h: ModelTurn(text=f"Your fit score is {last_tool_result(h, 'match_skills')['fit_score']}%."),
        ]
    )
    agent = Agent(llm, ctx)
    reply = agent.chat("How well do I fit this job? " + SAMPLE_JOB)

    assert reply.text == "Your fit score is 43%."
    assert [s.tool for s in reply.trace] == ["get_resume", "save_job_description", "match_skills"]
    assert all(s.ok for s in reply.trace)
    # history: user, model, tool, model, tool, model
    assert [m["role"] for m in agent.history] == ["user", "model", "tool", "model", "tool", "model"]


def test_tool_errors_are_reported_back_to_model(ctx):
    llm = FakeLLM(
        [
            ModelTurn(text=None, tool_calls=[call("match_skills", job_id="nope")]),
            lambda h: ModelTurn(text="Error seen: " + last_tool_result(h, "match_skills")["error"]),
        ]
    )
    reply = Agent(llm, ctx).chat("score it")
    assert reply.trace[0].ok is False
    assert reply.text.startswith("Error seen: Unknown job_id")


def test_step_limit_stops_runaway_loops(ctx):
    llm = FakeLLM([ModelTurn(text=None, tool_calls=[call("list_applications")]) for _ in range(3)])
    reply = Agent(llm, ctx, max_steps=3).chat("loop forever")
    assert reply.stopped_early
    assert len(reply.trace) == 3


def test_long_results_are_truncated_in_trace(ctx):
    ctx.resume_text = "Python developer. " * 200
    llm = FakeLLM([ModelTurn(text=None, tool_calls=[call("get_resume")]), ModelTurn(text="ok")])
    reply = Agent(llm, ctx).chat("read my resume")
    assert len(reply.trace[0].result["resume_text"]) < 500
