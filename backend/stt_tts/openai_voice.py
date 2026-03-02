"""
Step 4: STT and TTS using OpenAI.

Concepts:
- STT (Speech-to-Text): We send an audio file (e.g. from the browser) and get back a transcript string.
  The browser typically records in WebM or WAV; OpenAI supports many formats (wav, webm, mp3, etc.).
- TTS (Text-to-Speech): We send the agent's reply text and get back binary audio (e.g. MP3).
  The client plays this with an <audio> element or AudioContext.
- We use a single OpenAI client and the same API key for both; you could swap to other providers
  (e.g. Deepgram for STT, ElevenLabs for TTS) by replacing this module.
"""

from openai import OpenAI


def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Speech-to-Text: convert uploaded audio to text.
    audio_bytes: raw bytes of the audio file (e.g. webm, wav, mp3).
    filename: hint for content type (extension matters for some APIs).
    Returns the transcript string.
    """
    client = OpenAI()
    # OpenAI Python API expects a file-like object; we use BytesIO
    from io import BytesIO
    file_like = BytesIO(audio_bytes)
    file_like.name = filename
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=file_like,
    )
    return response.text.strip() if response.text else ""


def synthesize_speech(text: str) -> bytes:
    """
    Text-to-Speech: convert reply text to audio bytes (MP3).
    Returns bytes suitable to return as response body with Content-Type: audio/mpeg.
    """
    if not text.strip():
        # Return minimal silent MP3 or a very short phrase to avoid API error
        text = "Okay."
    client = OpenAI()
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
    )
    return response.content
