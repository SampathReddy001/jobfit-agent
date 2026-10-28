"""Deterministic skill extraction and resume-to-job matching.

The LLM is good at reading and writing, but a fit score should be
reproducible: the same resume and job should always score the same. So the
score comes from this plain-Python matcher, and the model explains it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# canonical name -> extra aliases (the canonical name itself is always matched)
SKILLS: dict[str, list[str]] = {
    # Languages
    "Python": [],
    "JavaScript": ["JS", "ES6"],
    "TypeScript": ["TS"],
    "Java": [],
    "C++": ["cpp"],
    "C#": ["csharp"],
    "Go": ["Golang"],
    "Rust": [],
    "Kotlin": [],
    "Swift": [],
    "PHP": [],
    "Ruby": [],
    "Scala": [],
    "SQL": [],
    "Bash": ["shell scripting"],
    "HTML": ["HTML5"],
    "CSS": ["CSS3"],
    # Frontend
    "React": ["React.js", "ReactJS"],
    "Next.js": ["NextJS"],
    "Vue": ["Vue.js", "VueJS"],
    "Angular": [],
    "Redux": [],
    "Tailwind CSS": ["Tailwind"],
    "Bootstrap": [],
    "Vite": [],
    # Backend
    "Node.js": ["Node", "NodeJS"],
    "Express": ["Express.js", "ExpressJS"],
    "FastAPI": [],
    "Flask": [],
    "Django": [],
    "Spring Boot": [],
    "GraphQL": [],
    "REST APIs": ["REST", "RESTful", "REST API"],
    "Microservices": ["microservice"],
    # Data stores
    "PostgreSQL": ["Postgres"],
    "MySQL": [],
    "MongoDB": ["Mongo", "Mongoose"],
    "Redis": [],
    "SQLite": [],
    "Elasticsearch": [],
    "Snowflake": [],
    "BigQuery": [],
    # Data & ML
    "pandas": [],
    "NumPy": [],
    "scikit-learn": ["sklearn", "scikit learn"],
    "TensorFlow": [],
    "PyTorch": [],
    "Keras": [],
    "XGBoost": [],
    "Machine Learning": ["ML"],
    "Deep Learning": ["neural networks", "neural network"],
    "NLP": ["natural language processing"],
    "Computer Vision": ["OpenCV"],
    "LLMs": ["LLM", "large language models", "large language model", "GPT", "Gemini", "Claude"],
    "RAG": ["retrieval-augmented generation", "retrieval augmented generation"],
    "AI Agents": ["agentic", "AI agent", "tool calling", "function calling"],
    "Hugging Face": ["HuggingFace", "transformers"],
    "LangChain": [],
    "Vector Databases": ["vector database", "Pinecone", "FAISS", "Chroma", "pgvector"],
    "Data Analysis": ["data analytics", "exploratory data analysis", "EDA"],
    "Data Visualization": ["Matplotlib", "Seaborn", "Plotly", "D3.js", "D3"],
    "Tableau": [],
    "Power BI": ["PowerBI"],
    "Statistics": ["statistical"],
    "Spark": ["PySpark", "Apache Spark"],
    "Airflow": [],
    "ETL": ["data pipelines", "data pipeline"],
    "Jupyter": ["Jupyter Notebook"],
    "MLOps": ["MLflow", "model deployment"],
    # Cloud & DevOps
    "AWS": ["Amazon Web Services", "EC2", "S3", "Lambda"],
    "Azure": [],
    "GCP": ["Google Cloud"],
    "Docker": ["containers", "containerization"],
    "Kubernetes": ["k8s"],
    "Terraform": [],
    "CI/CD": ["GitHub Actions", "Jenkins", "continuous integration"],
    "Linux": ["Unix"],
    "Git": ["GitHub", "GitLab", "version control"],
    "Nginx": [],
    # Practices
    "Unit Testing": ["pytest", "Jest", "unit tests", "test-driven", "TDD"],
    "Agile": ["Scrum", "Kanban"],
    "System Design": ["distributed systems", "scalable systems"],
    "Data Structures & Algorithms": ["data structures", "algorithms", "DSA"],
    "Authentication": ["JWT", "OAuth", "auth"],
    "Security": ["cybersecurity", "application security"],
}

# Short aliases that are only safe to match with exact case ("Go", not "go").
_CASE_SENSITIVE = {"Go", "JS", "TS", "ML", "EDA", "S3", "D3", "GPT", "Node", "REST", "auth"}

# Headings that usually introduce optional requirements in a job post.
_NICE_TO_HAVE = re.compile(r"(nice[- ]to[- ]have|preferred|bonus|pluses|a plus|good to have|desired|optional)", re.I)
_REQUIRED = re.compile(
    r"(requirements|required|qualifications|must[- ]have|what you('|’)ll need|you have|minimum)", re.I
)


def _pattern(term: str) -> re.Pattern[str]:
    # Word-ish boundaries that still work for terms like "C++", "C#", "Node.js".
    escaped = re.escape(term)
    flags = 0 if term in _CASE_SENSITIVE else re.I
    return re.compile(rf"(?<![\w+#.]){escaped}(?![\w+#])", flags)


_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    name: [_pattern(t) for t in [name, *aliases]] for name, aliases in SKILLS.items()
}


def extract_skills(text: str) -> list[str]:
    """Return canonical skill names mentioned anywhere in `text`."""
    if not text:
        return []
    return [name for name, pats in _PATTERNS.items() if any(p.search(text) for p in pats)]


def split_requirements(job_text: str) -> tuple[str, str]:
    """Split a job post into (required-ish text, nice-to-have text).

    Heuristic: lines after a "Preferred / Nice to have / Bonus" heading count
    as optional until a "Requirements / Qualifications" heading appears.
    """
    required, optional, in_optional = [], [], False
    for line in job_text.splitlines():
        stripped = line.strip()
        is_heading = len(stripped) < 60 and not stripped.startswith(("-", "•", "*"))
        if is_heading and _NICE_TO_HAVE.search(stripped):
            in_optional = True
        elif is_heading and _REQUIRED.search(stripped):
            in_optional = False
        (optional if in_optional else required).append(line)
    return "\n".join(required), "\n".join(optional)


@dataclass
class MatchResult:
    score: int | None
    matched_required: list[str]
    missing_required: list[str]
    matched_nice_to_have: list[str]
    missing_nice_to_have: list[str]
    extra_resume_skills: list[str]

    def as_dict(self) -> dict:
        return {
            "fit_score": self.score,
            "matched_required": self.matched_required,
            "missing_required": self.missing_required,
            "matched_nice_to_have": self.matched_nice_to_have,
            "missing_nice_to_have": self.missing_nice_to_have,
            "other_resume_skills": self.extra_resume_skills,
            "method": "Required skills weigh 1.0, nice-to-have 0.5. Score = matched weight / total weight.",
        }


def match(resume_text: str, job_text: str) -> MatchResult:
    resume = set(extract_skills(resume_text))
    req_text, opt_text = split_requirements(job_text)
    required = extract_skills(req_text)
    optional = [s for s in extract_skills(opt_text) if s not in required]

    total = len(required) + 0.5 * len(optional)
    got = sum(1 for s in required if s in resume) + 0.5 * sum(1 for s in optional if s in resume)
    score = round(100 * got / total) if total else None

    job_all = set(required) | set(optional)
    return MatchResult(
        score=score,
        matched_required=[s for s in required if s in resume],
        missing_required=[s for s in required if s not in resume],
        matched_nice_to_have=[s for s in optional if s in resume],
        missing_nice_to_have=[s for s in optional if s not in resume],
        extra_resume_skills=sorted(resume - job_all),
    )
