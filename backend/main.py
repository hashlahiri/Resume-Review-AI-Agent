from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
import requests
import json

from pypdf import PdfReader
from docx import Document

from prompt import SYSTEM_PROMPT, JSON_SCHEMA_HINT

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "mistral"

app = FastAPI(title="AI Resume Reviewer Agent (Local)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BulletRewrite(BaseModel):
    original: str
    improved: str
    why: str


class RoleFit(BaseModel):
    target_role: str
    fit_level: Literal["low", "medium", "high"]
    why: str


class ReviewResponse(BaseModel):
    score: float = Field(..., ge=0, le=100)
    summary: str
    strengths: List[str]
    gaps: List[str]
    ats_keywords_missing: List[str]
    bullet_rewrites: List[BulletRewrite]
    role_fit: RoleFit
    next_actions_7_days: List[str]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    from io import BytesIO
    try:
        bio = BytesIO(file_bytes)
        reader = PdfReader(bio)

        # handle encrypted PDFs
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")  # try empty password
            except Exception:
                return ""

        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()
    except Exception:
        return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    # python-docx reads from a path-like object; easiest is to write to memory via bytes->temp
    # but can load via BytesIO safely
    from io import BytesIO
    bio = BytesIO(file_bytes)
    doc = Document(bio)
    return "\n".join([p.text for p in doc.paragraphs]).strip()


def extract_resume_text(upload: UploadFile, file_bytes: bytes) -> str:
    name = (upload.filename or "").lower()
    ctype = (upload.content_type or "").lower()

    if name.endswith(".pdf") or "pdf" in ctype:
        return extract_text_from_pdf(file_bytes)
    if name.endswith(".docx") or "word" in ctype or "officedocument" in ctype:
        return extract_text_from_docx(file_bytes)
    # fallback: treat as text
    try:
        return file_bytes.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def call_ollama(model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
        }
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "")


def robust_json_parse(text: str) -> dict:
    """
    Models sometimes add extra text. We try to extract the first JSON object.
    """
    text = text.strip()

    # Fast path
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to extract JSON object boundaries
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        return json.loads(candidate)

    raise ValueError("Could not parse JSON from model output.")


@app.get("/health")
def health():
    return {"ok": True, "ollama_url": OLLAMA_URL, "default_model": DEFAULT_MODEL}


@app.post("/review", response_model=ReviewResponse)
async def review_resume(
    file: UploadFile = File(...),
    target_role: str = Form("Backend Software Engineer"),
    model: str = Form(DEFAULT_MODEL),
):
    file_bytes = await file.read()
    resume_text = extract_resume_text(file, file_bytes)

    if not resume_text or len(resume_text) < 200:
        return {
            "score": 0,
            "summary": "Resume text extraction failed or too little text was found. Please upload a clearer PDF/DOCX or a text resume.",
            "strengths": [],
            "gaps": ["Could not extract enough text to review."],
            "ats_keywords_missing": [],
            "bullet_rewrites": [],
            "role_fit": {"target_role": target_role, "fit_level": "low", "why": "No content to evaluate."},
            "next_actions_7_days": ["Re-upload the resume as a text-based PDF or DOCX (not scanned images)."]
        }

    user_prompt = f"""
{SYSTEM_PROMPT}

{JSON_SCHEMA_HINT}

Target role: {target_role}

Resume:
\"\"\"
{resume_text}
\"\"\"

Now produce the JSON.
"""

    raw = call_ollama(model=model, prompt=user_prompt)

    try:
        parsed = robust_json_parse(raw)
    except Exception as e:
        # Retry once with stricter instruction
        retry_prompt = f"""
Return ONLY valid JSON. No prose. No markdown. No code fences.

Schema:
{JSON_SCHEMA_HINT}

Target role: {target_role}

Resume:
\"\"\"
{resume_text}
\"\"\"
"""
        raw2 = call_ollama(model=model, prompt=retry_prompt)
        parsed = robust_json_parse(raw2)

    return parsed
