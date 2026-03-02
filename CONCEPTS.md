# Voice Agent: Concepts & System Design (In-Depth)

This document explains **every concept** behind building a production-style voice agent. Read it as we build each step; sections map to implementation steps.

---

## Part 1: The Big Picture — What Is a Voice Agent?

A **voice agent** is a system that:

1. **Listens** — converts the user’s speech to text (Speech-to-Text, STT).
2. **Thinks** — interprets intent, may call tools (e.g. look up an order), and produces a text reply (LLM + optional tools).
3. **Speaks** — converts the reply text to speech (Text-to-Speech, TTS) and plays it.

So the pipeline is: **Audio In → STT → Text → Agent (LLM + Tools) → Text → TTS → Audio Out.**

This is often called the **"sandwich"** or **cascaded** architecture: two audio layers (STT, TTS) with a "brain" in the middle. The alternative is **speech-to-speech** (one model that goes directly from audio to audio), which we are *not* using so we can keep full control over the middle layer (tools, prompts, providers).

---

## Part 2: System Design — The Pipeline in Detail

```
┌─────────────┐     audio      ┌─────────────┐    transcript     ┌─────────────────────────────┐
│   Client    │ ──────────────► │     STT     │ ────────────────► │  Agent (LLM + Tools)         │
│  (browser)  │                 │  (API call) │                   │  - system prompt           │
│             │                 └─────────────┘                   │  - conversation history    │
│  Mic → WS   │                                                    │  - tool calls (order lookup)│
│  WS → Spk   │     audio      ┌─────────────┐    reply text      │  - streamed or full reply   │
│             │ ◄────────────  │     TTS     │ ◄───────────────── │                             │
└─────────────┘                 │  (API call) │                   └─────────────────────────────┘
                                └─────────────┘
```

### Why this order?

- **STT first**: We need text before the LLM can reason. Streaming STT can send partial transcripts so the agent can react sooner (we'll start with "full utterance" for simplicity).
- **Agent in the middle**: All business logic (order status, reorder, FAQ) lives here. The LLM decides *when* to call tools and *how* to phrase the answer.
- **TTS last**: Only after we have the final (or chunked) reply text do we synthesize speech. In advanced setups, TTS can start as soon as the first sentence is ready (streaming).

### Latency

- **STT**: ~100–500 ms (depends on provider and utterance length).
- **LLM**: ~200 ms–2 s (depends on model and reply length).
- **TTS**: ~100–300 ms to first audio.
- **Total**: We aim for **under ~1–2 seconds** to first word for a good experience. Streaming (sentence-by-sentence TTS) helps.

---

## Part 3: Key Concepts (Mapped to Implementation)

### 3.1 Domain & Tools (Steps 1–2)

- **Domain**: The "world" the agent operates in (e.g. orders, tracking, reorder). We model it with **data** (orders, customers) and **operations** (get status, reorder).
- **Tools**: Python functions the LLM is allowed to call. Each tool has a **name**, **description** (used by the LLM to decide when to call it), and **parameters** (e.g. `order_id`). The LLM outputs "call tool X with args Y"; the runtime runs the function and returns the result to the LLM so it can reply in natural language.
- **Mock data**: For a portfolio project we don't need a real DB. We use JSON or in-memory structures so the tools return realistic data. Same interface, swap to a real DB later.

### 3.2 Agent Loop (Step 3)

- **System prompt**: Instructions that define the agent's role (e.g. "You are QuickBite support. Be concise. Use tools to look up orders.").
- **Conversation history**: List of messages (user, assistant, and optionally tool results). The LLM sees this so it can do multi-turn dialogue and reference "your last order."
- **Tool-calling loop**: (1) User message (+ history) → LLM. (2) If LLM says "call tool X with Y" → we run the function → add tool result to messages → call LLM again. (3) Repeat until LLM returns a normal text reply (no more tool calls). That final reply is what we send to the user (and later to TTS).

### 3.3 Session & Memory (Step 3)

- **Session ID**: Each conversation has an ID. We store history per session (in memory for now). So "reorder my last order" can be resolved because we have the previous messages and tool results in that session.

### 3.4 STT & TTS (Step 4)

- **STT (Speech-to-Text)**: Input = audio (e.g. WAV/WebM). Output = text. We'll use an API (e.g. OpenAI Whisper or similar) that accepts a file or stream and returns a transcript.
- **TTS (Text-to-Speech)**: Input = text. Output = audio. We'll use an API that returns an audio file or stream. For turn-based v1 we can send the full reply and get one audio back.
- **Formats**: Backend and client must agree on sample rate and format (e.g. 16 kHz mono for STT, 24 kHz for playback). We'll document what we use.

### 3.5 Turn-based vs Streaming (Step 4)

- **Turn-based (what we build first)**: User presses "Talk", speaks, releases. We send the whole recording → STT → Agent → TTS → play full response. Simple and easy to debug.
- **Streaming (later)**: Send audio chunks as the user speaks; STT streams partial transcripts; agent can start early; TTS streams sentence-by-sentence. Lower latency but more moving parts. We'll add this after the turn-based flow works.

---

## Part 4: Project Layout (Why This Structure)

```
backend/
  main.py           # FastAPI app, routes: /health, /chat, /voice
  agent/            # Agent logic (prompts, tools wiring, memory)
  tools/            # Tool implementations (order status, reorder, etc.)
  data/             # Mock data (orders.json, etc.)
  stt_tts/          # STT and TTS client wrappers
  requirements.txt
frontend/
  index.html
  app.js            # Mic, WebSocket or fetch, audio playback, transcript UI
docs/
  CONCEPTS.md       # Same content as this file
  SYSTEM_DESIGN.md  # High-level diagram + decisions (written in Phase 4)
```

- **Separation of concerns**: Routes in `main.py`, agent in `agent/`, tools in `tools/`, so we can test and reason about each part.
- **Mock data in `data/`**: Keeps fixtures and schema in one place; tools load or import from here.

---

## Part 5: Step 0 — Project Setup (What You Just Got)

- **Virtual environment**: Always use a venv so dependencies don't pollute the system. Create with `python -m venv .venv`, activate, then `pip install -r backend/requirements.txt`.
- **requirements.txt**: Pins FastAPI, LangChain, OpenAI, etc. Anyone cloning the repo can reproduce the same environment.
- **Folder layout**: `main.py` = routes only; `agent/` = LLM + prompts; `tools/` = order/tracking logic; `data/` = mock JSON. This separation lets you test the agent and tools without starting the server.
- **CORS**: The browser frontend will call the API (often from a different port). CORS middleware allows those requests; in production you'd restrict `allow_origins` to your frontend URL.
- **.env.example**: API keys go in `.env` (never committed). Code loads them via `python-dotenv` or `os.getenv("OPENAI_API_KEY")`.

Run the server: from `backend/`, run `uvicorn main:app --reload`. Then open `http://localhost:8000/health` — you should see `{"status":"ok"}`.

---

## Part 6: Step 1–2 — Mock Data & Tools (What You Have)

- **orders.json**: Each order has `order_id`, `customer_id`, `status`, `items`, `eta_minutes`, `tracking`. Tools read this file. Adding or editing JSON is how you "change the world" the agent sees.
- **Tool contract**: Each tool has a **name** (e.g. `get_order_status`), a **description** (the LLM uses this to decide when to call it), and **parameters** (e.g. `order_id: Optional[str]`). The LLM outputs a tool call; our code runs the function and passes the result back as a `ToolMessage`.
- **customer_id**: We inject it in the agent (via system prompt and wrapped tools) so the LLM doesn't have to "know" it; it only passes `order_id` or nothing. For demo we use `cust-alice`; in production this comes from auth.

---

## Part 7: Step 3 — Agent Loop & /chat (What You Have)

- **System prompt**: Defines role (QuickBite assistant), style (concise, no markdown), and current `customer_id`. The model follows this for every turn.
- **Conversation history**: Stored per `session_id` in `_sessions`. Each turn we send [system, ...history, new_user_message]. After the turn we append the user message and the final assistant message so the next turn has context (e.g. "reorder my last order").
- **Tool-calling loop**: `invoke(messages)` → if `response.tool_calls` is non-empty, run each tool, append `ToolMessage`s to `messages`, invoke again. When the model returns a response with no tool_calls, that's the final reply we return and store.
- **/chat**: POST `{ "session_id": "...", "message": "Where's my order?" }` → returns `{ "reply": "..." }`. Optional `customer_id` in the body for multi-tenant.

---

## Part 8: Step 4 — STT & TTS & /voice (What You Have)

- **STT**: Browser sends recorded audio (e.g. WebM). We call OpenAI's transcription API and get a single transcript string. That string is the "user message" for the agent.
- **TTS**: We take the agent's text reply and call OpenAI's speech API to get MP3 bytes. We return them as base64 in JSON so the frontend can decode and play without a second request.
- **/voice** flow: `audio file → transcribe() → chat() → synthesize_speech() → JSON(transcript, reply, audio_base64)`.
- **Form upload**: We use `Form()` for `session_id` (and optional `customer_id`) and `File()` for the audio so the client can use a single multipart request.

---

## Part 9: Step 5 — Frontend Voice Loop (What You Have)

- **getUserMedia**: We request the microphone and get a `MediaStream`. We pass it to `MediaRecorder` to record into chunks, then combine into one `Blob` when the user releases the button.
- **Session ID**: We generate one per tab (e.g. `sess-xxx`) and store it in `sessionStorage` so all turns in that tab share the same conversation history on the backend.
- **Playback**: We decode `audio_base64` to binary, create a `Blob`, then an object URL, and play it with `new Audio(url).play()`. When playback ends we revoke the object URL.
- **CORS**: The backend has `allow_origins=["*"]` so the frontend (e.g. file:// or another port) can call the API. In production you'd restrict this.

---

## Part 10: Build order summary

| Step | What we build | What you learn |
|------|----------------|----------------|
| 0 | Project setup, venv, `requirements.txt`, folders | Repo hygiene, dependency pinning |
| 1 | Mock data (orders, customers), schema | Domain modeling, "contract" for tools |
| 2 | Tool functions (get_order_status, reorder, get_tracking) | Tool contract, how LLM will call them |
| 3 | LangChain agent + `/chat` endpoint, session memory | Agent loop, prompts, tool-calling, state |
| 4 | STT + TTS wrappers, `/voice` endpoint | Sandwich pipeline, audio formats |
| 5 | Frontend: mic → upload → play response + transcript | End-to-end voice loop, browser APIs |
| 6 | `SYSTEM_DESIGN.md`, logging, README demo | How to present the system to others |

We'll implement in this order so each step has a clear concept and you can run/test before adding the next layer.
