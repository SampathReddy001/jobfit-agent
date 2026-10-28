"""Turn an uploaded resume file into plain text."""

from __future__ import annotations

import io

from pypdf import PdfReader

MAX_RESUME_BYTES = 5 * 1024 * 1024
MAX_RESUME_CHARS = 20_000


class ResumeError(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_RESUME_BYTES:
        raise ResumeError("Resume file is larger than 5 MB.")
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise ResumeError(f"Could not read that PDF: {exc}") from exc
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace")
    else:
        raise ResumeError("Please upload a PDF, .txt or .md resume.")

    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(text) < 50:
        raise ResumeError("Couldn't find text in that file. If it's a scanned PDF, export a text-based PDF instead.")
    return text[:MAX_RESUME_CHARS]
