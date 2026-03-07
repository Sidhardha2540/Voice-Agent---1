"""
Voice Agent — FastAPI entry point.

Concepts:
- FastAPI runs your HTTP and WebSocket routes.
- We'll add /health (Step 0), /chat (Step 3), /voice (Step 4).
- Keeping routes here and heavy logic in agent/ and tools/ keeps the pipeline clear.
"""

import logging
from pathlib import Path

import base64
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.runner import chat
from stt_tts.openai_voice import transcribe, synthesize_speech
from tools.order_tools import get_order_status, get_tracking_info

from dotenv import load_dotenv

# Load .env from project root (parent of backend/) so OPENAI_API_KEY is set
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Voice Agent (QuickBite)",
    description="E-commerce voice agent: order status, tracking, reorder.",
    version="0.1.0",
)

# Allow browser frontend on another port or same machine to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """
    Step 0: Liveness check.
    Use this to verify the server is up (e.g. in CI or from the frontend).
    """
    return {"status": "ok", "service": "voice-agent"}


# --- Sample order APIs (useful for testing tools without the agent/voice) ---


class OrderStatusResponse(BaseModel):
    customer_id: str
    order_id: str | None = None
    status: str


@app.get("/orders/status", response_model=OrderStatusResponse)
def order_status(customer_id: str = "cust-alice", order_id: str | None = None):
    """
    Get the status text for an order using the same logic as the agent tools.
    If order_id is not provided, returns the most recent order for the customer.
    """
    status_text = get_order_status(customer_id, order_id)
    return OrderStatusResponse(customer_id=customer_id, order_id=order_id, status=status_text)


class OrderTrackingResponse(BaseModel):
    customer_id: str
    order_id: str | None = None
    tracking: str


@app.get("/orders/tracking", response_model=OrderTrackingResponse)
def order_tracking(customer_id: str = "cust-alice", order_id: str | None = None):
    """
    Get tracking information text for an order (driver, step, ETA).
    Mirrors the get_tracking_info tool used by the agent.
    """
    tracking_text = get_tracking_info(customer_id, order_id)
    return OrderTrackingResponse(customer_id=customer_id, order_id=order_id, tracking=tracking_text)


# --- Step 3: Text chat ---

class ChatRequest(BaseModel):
    session_id: str
    message: str
    customer_id: str | None = None


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """
    Send a text message, get the agent's reply (with tool use and conversation memory).
    """
    logger.info("chat session_id=%s message_len=%d", req.session_id, len(req.message or ""))
    reply = chat(session_id=req.session_id, user_message=req.message, customer_id=req.customer_id)
    logger.info("chat session_id=%s reply_len=%d", req.session_id, len(reply or ""))
    return ChatResponse(reply=reply)


# --- Step 4: Turn-based voice (audio in → transcript → agent → TTS → audio out) ---

class VoiceResponse(BaseModel):
    transcript: str
    reply: str
    audio_base64: str


@app.post("/voice", response_model=VoiceResponse)
async def voice_endpoint(
    session_id: str = Form(...),
    customer_id: str | None = Form(None),
    audio: UploadFile = File(...),
):
    """
    Voice turn: upload audio → STT → agent → TTS → return transcript, reply, and audio (base64).
    Frontend records mic, sends the file here, then plays the returned audio and shows transcript/reply.
    """
    audio_bytes = await audio.read()
    filename = audio.filename or "audio.webm"
    logger.info("voice session_id=%s audio_size=%d", session_id, len(audio_bytes))
    transcript = transcribe(audio_bytes, filename)
    reply = chat(session_id=session_id, user_message=transcript, customer_id=customer_id)
    audio_bytes_out = synthesize_speech(reply)
    logger.info("voice session_id=%s transcript_len=%d reply_len=%d", session_id, len(transcript or ""), len(reply or ""))
    return VoiceResponse(
        transcript=transcript,
        reply=reply,
        audio_base64=base64.b64encode(audio_bytes_out).decode("utf-8"),
    )
