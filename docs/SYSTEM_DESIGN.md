# Voice Agent — System Design

## Architecture (Turn-based v1)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Browser                                                                  │
│  - Mic → MediaRecorder → Blob (audio/webm)                                │
│  - POST /voice (FormData: session_id, audio)                              │
│  - Response: { transcript, reply, audio_base64 } → show text, play audio │
└──────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                                        │
│  1. STT:  audio bytes → OpenAI Whisper → transcript (text)                │
│  2. Agent: transcript + session history → LLM + tools → reply (text)      │
│  3. TTS:  reply → OpenAI TTS → audio bytes (MP3)                          │
│  4. Return transcript, reply, base64(audio)                               │
└──────────────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Role | Current choice | Swap later |
|-----------|------|----------------|------------|
| STT | Audio → text | OpenAI Whisper | Deepgram, AssemblyAI |
| Agent | Text → tools + reply | LangChain + GPT-4o-mini | Other LLM / framework |
| TTS | Text → audio | OpenAI TTS | ElevenLabs, Cartesia |
| Memory | Per-session history | In-memory dict | Redis, DB |

## Latency (typical)

- STT: ~200–500 ms
- LLM + tools: ~300–1500 ms
- TTS: ~200–500 ms  
- **Total to first byte**: ~1–2.5 s (turn-based). Streaming (future) would reduce perceived latency.

## Design decisions

- **Turn-based first**: Simpler to build and debug; streaming can be added once this works.
- **Session in memory**: Fine for single-process demo; use Redis or DB for scale.
- **customer_id in request**: Optional; default `cust-alice` for demo. In production, derive from auth.
- **Tools return strings**: LLM gets a short, consistent format to phrase the answer.
