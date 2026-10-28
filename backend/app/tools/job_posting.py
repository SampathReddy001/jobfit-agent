"""Tools for loading job postings, from a URL or from pasted text."""

from __future__ import annotations

import ipaddress
import socket
import uuid
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .registry import ToolContext, tool

MAX_JOB_CHARS = 12_000
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobFitAgent/1.0; +https://github.com/SampathReddy001)"}


def _is_public_url(url: str) -> bool:
    """Block requests to localhost / private networks (basic SSRF protection)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def html_to_text(html: str) -> tuple[str, str]:
    """Return (page title, readable text) from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form"]):
        tag.decompose()
    title = (soup.title.string or "").strip() if soup.title else ""
    main = soup.find("main") or soup.find("article") or soup.body or soup
    lines = (line.strip() for line in main.get_text("\n").splitlines())
    text = "\n".join(line for line in lines if line)
    return title, text


def _store(ctx: ToolContext, company: str, title: str, text: str, url: str | None) -> dict:
    job_id = uuid.uuid4().hex[:8]
    ctx.jobs[job_id] = {"company": company, "title": title, "text": text, "url": url}
    return {"job_id": job_id, "company": company, "title": title, "url": url, "text": text}


@tool(
    name="fetch_job_posting",
    description=(
        "Download a job posting from a public URL and return its text. "
        "Returns a job_id to use with match_skills. Some sites (e.g. LinkedIn) block "
        "automated access; if this fails, ask the user to paste the job description."
    ),
    parameters={
        "type": "object",
        "properties": {"url": {"type": "string", "description": "Full http(s) URL of the job posting"}},
        "required": ["url"],
    },
)
def fetch_job_posting(ctx: ToolContext, url: str) -> dict:
    if not _is_public_url(url):
        return {"error": "That URL is not a public http(s) address, so it was not fetched."}
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return {"error": f"Could not download the page: {exc}. Ask the user to paste the job text."}

    title, text = html_to_text(resp.text)
    if len(text) < 200:
        return {
            "error": "The page had almost no readable text (it may need JavaScript or a login). "
            "Ask the user to paste the job description."
        }
    return _store(ctx, company="", title=title, text=text[:MAX_JOB_CHARS], url=url)


@tool(
    name="save_job_description",
    description=(
        "Store a job description the user pasted into the chat so it can be analyzed. "
        "Returns a job_id to use with match_skills."
    ),
    parameters={
        "type": "object",
        "properties": {
            "company": {"type": "string", "description": "Company name, if known"},
            "title": {"type": "string", "description": "Job title, if known"},
            "description": {"type": "string", "description": "The full job description text"},
        },
        "required": ["description"],
    },
)
def save_job_description(ctx: ToolContext, description: str, company: str = "", title: str = "") -> dict:
    stored = _store(ctx, company=company, title=title, text=description[:MAX_JOB_CHARS], url=None)
    stored.pop("text")  # the model already has the text; don't echo it back
    return stored
