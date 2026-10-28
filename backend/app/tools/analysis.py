"""Tools for reading the resume, scoring fit, and finding learning resources."""

from __future__ import annotations

from urllib.parse import quote_plus

from .. import skills
from .registry import ToolContext, tool

# Free, reputable starting points for common skills.
RESOURCES: dict[str, list[dict[str, str]]] = {
    "Python": [{"title": "Official Python Tutorial", "url": "https://docs.python.org/3/tutorial/"}],
    "JavaScript": [
        {"title": "MDN JavaScript Guide", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide"}
    ],
    "TypeScript": [{"title": "TypeScript Handbook", "url": "https://www.typescriptlang.org/docs/handbook/intro.html"}],
    "React": [{"title": "react.dev: Learn React", "url": "https://react.dev/learn"}],
    "Next.js": [{"title": "Next.js Learn course", "url": "https://nextjs.org/learn"}],
    "Node.js": [{"title": "Node.js Learn", "url": "https://nodejs.org/en/learn"}],
    "FastAPI": [{"title": "FastAPI Tutorial", "url": "https://fastapi.tiangolo.com/tutorial/"}],
    "Django": [{"title": "Django Tutorial", "url": "https://docs.djangoproject.com/en/stable/intro/tutorial01/"}],
    "SQL": [{"title": "SQLBolt interactive lessons", "url": "https://sqlbolt.com/"}],
    "PostgreSQL": [{"title": "PostgreSQL Tutorial", "url": "https://www.postgresql.org/docs/current/tutorial.html"}],
    "MongoDB": [{"title": "MongoDB University", "url": "https://learn.mongodb.com/"}],
    "pandas": [{"title": "pandas Getting Started", "url": "https://pandas.pydata.org/docs/getting_started/index.html"}],
    "scikit-learn": [{"title": "scikit-learn User Guide", "url": "https://scikit-learn.org/stable/user_guide.html"}],
    "Machine Learning": [
        {"title": "Google ML Crash Course", "url": "https://developers.google.com/machine-learning/crash-course"}
    ],
    "Deep Learning": [{"title": "fast.ai Practical Deep Learning", "url": "https://course.fast.ai/"}],
    "PyTorch": [{"title": "PyTorch Tutorials", "url": "https://pytorch.org/tutorials/"}],
    "TensorFlow": [{"title": "TensorFlow Tutorials", "url": "https://www.tensorflow.org/tutorials"}],
    "NLP": [{"title": "Hugging Face NLP Course", "url": "https://huggingface.co/learn/nlp-course"}],
    "Hugging Face": [{"title": "Hugging Face Learn", "url": "https://huggingface.co/learn"}],
    "LLMs": [{"title": "Hugging Face LLM Course", "url": "https://huggingface.co/learn/llm-course"}],
    "AI Agents": [{"title": "Hugging Face Agents Course", "url": "https://huggingface.co/learn/agents-course"}],
    "Docker": [{"title": "Docker Get Started", "url": "https://docs.docker.com/get-started/"}],
    "Kubernetes": [{"title": "Kubernetes Basics", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/"}],
    "AWS": [{"title": "AWS Skill Builder (free tier)", "url": "https://skillbuilder.aws/"}],
    "GCP": [{"title": "Google Cloud Skills Boost", "url": "https://www.cloudskillsboost.google/"}],
    "Azure": [{"title": "Microsoft Learn: Azure", "url": "https://learn.microsoft.com/en-us/training/azure/"}],
    "CI/CD": [{"title": "GitHub Actions Quickstart", "url": "https://docs.github.com/en/actions/quickstart"}],
    "Git": [{"title": "Pro Git book", "url": "https://git-scm.com/book/en/v2"}],
    "Linux": [{"title": "Linux Journey", "url": "https://linuxjourney.com/"}],
    "System Design": [{"title": "System Design Primer", "url": "https://github.com/donnemartin/system-design-primer"}],
    "Data Structures & Algorithms": [{"title": "NeetCode Roadmap", "url": "https://neetcode.io/roadmap"}],
    "Unit Testing": [
        {"title": "pytest Getting Started", "url": "https://docs.pytest.org/en/stable/getting-started.html"}
    ],
}


@tool(
    name="get_resume",
    description="Return the text of the resume the user uploaded, plus the skills detected in it.",
    parameters={"type": "object", "properties": {}},
)
def get_resume(ctx: ToolContext) -> dict:
    if not ctx.resume_text:
        return {"error": "No resume uploaded yet. Ask the user to upload one using the Resume panel."}
    return {"resume_text": ctx.resume_text, "detected_skills": skills.extract_skills(ctx.resume_text)}


@tool(
    name="match_skills",
    description=(
        "Compare the user's resume with a loaded job posting. Returns a reproducible fit score "
        "(0-100) with matched and missing required / nice-to-have skills. Always use this "
        "score instead of inventing one."
    ),
    parameters={
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "job_id from fetch_job_posting or save_job_description"}
        },
        "required": ["job_id"],
    },
)
def match_skills(ctx: ToolContext, job_id: str) -> dict:
    if not ctx.resume_text:
        return {"error": "No resume uploaded yet."}
    job = ctx.jobs.get(job_id)
    if job is None:
        return {"error": f"Unknown job_id '{job_id}'. Load the job first."}
    result = skills.match(ctx.resume_text, job["text"]).as_dict()
    if result["fit_score"] is None:
        result["note"] = "No known skills were detected in the job post; judge fit from the text instead."
    return result


@tool(
    name="find_learning_resources",
    description="Suggest free learning resources for skills the user is missing.",
    parameters={
        "type": "object",
        "properties": {
            "skills": {"type": "array", "items": {"type": "string"}, "description": "Skill names to find resources for"}
        },
        "required": ["skills"],
    },
)
def find_learning_resources(ctx: ToolContext, skills: list[str]) -> dict:
    out = {}
    for skill in skills[:10]:
        key = next((k for k in RESOURCES if k.lower() == skill.lower()), None)
        if key:
            out[skill] = RESOURCES[key]
        else:
            q = quote_plus(f"{skill} tutorial for beginners")
            out[skill] = [
                {"title": f"YouTube: {skill} tutorials", "url": f"https://www.youtube.com/results?search_query={q}"},
                {
                    "title": f"freeCodeCamp: {skill}",
                    "url": f"https://www.freecodecamp.org/news/search/?query={quote_plus(skill)}",
                },
            ]
    return {"resources": out}
