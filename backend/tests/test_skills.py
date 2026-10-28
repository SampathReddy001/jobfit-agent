from app import skills
from conftest import SAMPLE_JOB, SAMPLE_RESUME


def test_extracts_aliases_and_canonical_names():
    found = skills.extract_skills("Built APIs in NodeJS and Express.js, deployed with GitHub Actions on k8s")
    assert {"Node.js", "Express", "CI/CD", "Kubernetes"} <= set(found)


def test_short_aliases_are_case_sensitive():
    assert "Go" in skills.extract_skills("Backend services in Go and Rust")
    assert "Go" not in skills.extract_skills("Ready to go the extra mile")


def test_symbols_in_names():
    found = skills.extract_skills("Proficient in C++ and C#; some Node.js")
    assert {"C++", "C#", "Node.js"} <= set(found)


def test_split_requirements_separates_nice_to_have():
    required, optional = skills.split_requirements(SAMPLE_JOB)
    assert "Kubernetes" in optional and "Kubernetes" not in required
    assert "Python" in required


def test_match_scores_required_and_optional():
    result = skills.match(SAMPLE_RESUME, SAMPLE_JOB)
    # Required: Python, SQL, React, REST APIs, LLMs, Docker -> resume has Python, React, Docker
    assert set(result.matched_required) == {"Python", "React", "Docker"}
    assert set(result.missing_required) == {"SQL", "REST APIs", "LLMs"}
    # Optional: Kubernetes, PyTorch -> none matched. Score = 3 / (6 + 0.5*2) = 43%
    assert result.missing_nice_to_have == ["PyTorch", "Kubernetes"] or set(result.missing_nice_to_have) == {
        "PyTorch",
        "Kubernetes",
    }
    assert result.score == 43


def test_match_is_deterministic():
    assert skills.match(SAMPLE_RESUME, SAMPLE_JOB) == skills.match(SAMPLE_RESUME, SAMPLE_JOB)


def test_job_without_known_skills_has_no_score():
    assert skills.match(SAMPLE_RESUME, "We want a cheerful team player.").score is None
