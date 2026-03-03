# Contributing to Voice Agent

Thanks for your interest in contributing. Here’s how to get set up and run the project locally.

## Setup

1. Clone the repo and go into the backend:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` in the **project root** (parent of `backend/`) and set `OPENAI_API_KEY` if you’re using the web or voice endpoints.

## Running the backend

From the `backend/` directory:

```bash
uvicorn main:app --reload
```

Then open http://localhost:8000/docs for the API docs and http://localhost:8000/health to check the server.

## Running tests

From the `backend/` directory:

```bash
python -m unittest discover -s tests -v
```

Tests cover the order tools (status, tracking, reorder, FAQ). Add tests for new tools or endpoints when you add them.

## Suggesting changes

- Open an issue to discuss a feature or bug before a large change.
- Keep the same structure: routes in `main.py`, agent in `agent/`, tools in `tools/`, STT/TTS in `stt_tts/`.
- Update `README.md` or `docs/` if you change how to run or configure the project.
