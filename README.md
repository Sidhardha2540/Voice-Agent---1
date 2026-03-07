# Voice Agent (E-commerce / Delivery)

A voice agent project for an Amazon/DoorDash-style business: order status, tracking, reorder, and support—built to learn system design, real-time STT→LLM→TTS pipelines, and tool-augmented conversation.

## What this is

- **Goal**: Portfolio project demonstrating a production-style voice agent (speech-to-text → LLM agent with tools → text-to-speech).
- **Use case**: Customer-style interactions—e.g., “Where’s my order?”, “Track my delivery”, “Reorder my last order”, FAQ.
- **Stack (planned)**: Python, FastAPI, LangChain/LangGraph, streaming STT/TTS, simple web client.

## Status

- **Implemented**: Backend (FastAPI + LangChain agent + tools), STT/TTS (OpenAI), turn-based `/voice`, text chat + voice frontend, cancel-order tool, request logging. See **How to run** below.
- **Next**: Streaming, barge-in, or telephony (optional).

## How to run

1. **Backend** (from project root):
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   # Set OPENAI_API_KEY in .env (copy from .env.example)
   uvicorn main:app --reload
   ```
   Server: http://localhost:8000. Docs: http://localhost:8000/docs.

2. **Frontend**: Open `frontend/index.html` in a browser (or serve it with any static server). You can **type** a message (e.g. "Where's my order?") and click Send, or **hold the mic button** to talk—both use the same session and agent. The page shows backend connection status (green when the server is reachable).

## Running tests

From the `backend/` directory:

```bash
python -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full setup and contribution guidelines.

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness check |
| GET | `/orders/status` | Order status (query: `customer_id`, optional `order_id`) |
| GET | `/orders/tracking` | Tracking info (query: `customer_id`, optional `order_id`) |
| POST | `/chat` | Text message → agent reply (body: `session_id`, `message`, optional `customer_id`) |
| POST | `/voice` | Audio upload → transcript, reply, audio (form: `session_id`, `audio`) |

Interactive docs: http://localhost:8000/docs when the backend is running.

## Roadmap / TODO

- **Phase 1 – Core backend**
  - Set up FastAPI backend and basic `/health` endpoint
  - Define mock order data (orders, tracking info)
  - Implement Python tools: `get_order_status`, `reorder_last_order`, `get_tracking_info`

- **Phase 2 – Text chat agent**
  - Add LangChain-based agent with tools
  - Create `/chat` endpoint that accepts text and returns agent responses
  - Keep per-session conversation history

- **Phase 3 – Voice interface (turn-based)**
  - Add `/voice` endpoint: audio in → STT → agent → TTS → audio out
  - Build a minimal web client with mic button and audio playback
  - Display transcripts for user and agent

- **Phase 4 – Polish and docs**
  - Write `docs/SYSTEM_DESIGN.md` explaining architecture and trade-offs
  - Add logging for conversations and tool calls
  - Record a short demo or GIF for the README

## License

MIT
