# AI Resume Reviewer Agent (Local Build)

AI agent that reviews resumes and returns structured feedback:
# AI Resume Reviewer Agent (Local Build)

A lightweight, local AI agent that reviews software engineering resumes and returns structured, actionable feedback:

- Score (0–100)
- Clear summary
- Strengths and gaps
- Missing ATS keywords for a target role
- Bullet-level rewrites with reasoning
- Role-fit assessment
- A 7-day improvement plan

**Project layout**

- `backend/` — FastAPI service that calls a local Ollama model and returns JSON responses.
- `ui/` — Streamlit front-end that uploads resumes and displays the review.
- `examples/` — Example resume files to try the app locally.

## Tech

- FastAPI (backend)
- Streamlit (UI)
- Ollama (local LLM runtime — optional, recommended)

## Prerequisites

- Python 3.12 (or your project's configured version)
- (Optional) Ollama installed and a local model pulled, e.g. `mistral`

## Quick start (local)

1. Install backend dependencies:

```bash
python -m pip3 install -r backend/requirements.txt
```

2. Install UI dependencies:

```bash
python -m pip3 install -r ui/requirements.txt
```

3. (Optional) Install Ollama and pull a model if you want local inference:

```bash
# install ollama per https://ollama.ai
ollama pull mistral
```

4. Run the backend API (from repo root):

```bash
uvicorn backend.main:app --reload --port 8000
```

5. Run the Streamlit UI (in a separate terminal):

```bash
streamlit run ui/app.py
```

The UI will point to `http://localhost:8000` by default. Upload a PDF/DOCX/TXT resume and press "Review Resume".

## Example curl (backend only)

```bash
curl -X POST "http://localhost:8000/review" \
	-F "file=@examples/sample_resume.txt" \
	-F "target_role=Backend Software Engineer"
```

## Where the prompts live

The prompt templates used to instruct the LLM are in `backend/prompt.py`.

## Notes

- The backend expects the model to return strict JSON. `backend/main.py` contains logic to robustly parse the model output and retry if the response contains extra text.
- If you don't run Ollama locally, the API call to `http://localhost:11434` will fail; either run Ollama or adapt `call_ollama()` to point at another LLM endpoint.

---
Updated to better reflect the repository structure and usage.
NOTE: Dont run on python 3.14 versions as some of the dependencies can cause conflicts