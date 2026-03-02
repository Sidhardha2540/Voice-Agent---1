/**
 * Step 5: Turn-based voice frontend.
 *
 * Concepts:
 * - getUserMedia: capture microphone stream. We use MediaRecorder to record to a Blob.
 * - When user releases the button we stop recording, send the blob to POST /voice (FormData:
 *   session_id, optional customer_id, audio file).
 * - Response: { transcript, reply, audio_base64 }. We show transcript and reply, decode base64
 *   to a blob, create an object URL, and play it in an Audio element.
 * - session_id: we generate once (simple random id) so the backend keeps conversation history.
 */

(function () {
  const API_BASE = "http://localhost:8000";

  const recordBtn = document.getElementById("recordBtn");
  const statusEl = document.getElementById("status");
  const youSaidEl = document.getElementById("youSaid");
  const agentSaidEl = document.getElementById("agentSaid");
  const errorEl = document.getElementById("error");

  let mediaRecorder = null;
  let chunks = [];

  function setStatus(text) {
    statusEl.textContent = text;
  }
  function setError(text) {
    errorEl.textContent = text || "";
  }

  function randomSessionId() {
    return "sess-" + Math.random().toString(36).slice(2, 12);
  }
  const sessionId = sessionStorage.getItem("voiceAgentSessionId") || randomSessionId();
  sessionStorage.setItem("voiceAgentSessionId", sessionId);

  function startRecording() {
    setError("");
    setStatus("Listening… release to send.");
    recordBtn.classList.add("recording");
    chunks = [];
    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then((stream) => {
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) chunks.push(e.data);
        };
        mediaRecorder.onstop = () => {
          stream.getTracks().forEach((t) => t.stop());
          sendAudio();
        };
        mediaRecorder.start();
      })
      .catch((err) => {
        setError("Microphone access denied or unavailable: " + err.message);
        recordBtn.classList.remove("recording");
      });
  }

  function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === "inactive") return;
    recordBtn.classList.remove("recording");
    mediaRecorder.stop();
  }

  function sendAudio() {
    if (chunks.length === 0) {
      setStatus("No audio recorded. Try again.");
      return;
    }
    setStatus("Sending…");
    const blob = new Blob(chunks, { type: "audio/webm" });
    const form = new FormData();
    form.append("session_id", sessionId);
    form.append("audio", blob, "audio.webm");

    fetch(API_BASE + "/voice", {
      method: "POST",
      body: form,
    })
      .then((res) => {
        if (!res.ok) throw new Error(res.status + " " + res.statusText);
        return res.json();
      })
      .then((data) => {
        youSaidEl.textContent = data.transcript || "—";
        agentSaidEl.textContent = data.reply || "—";
        setStatus("Playing response…");
        playBase64Audio(data.audio_base64);
      })
      .catch((err) => {
        setError("Request failed: " + err.message);
        setStatus("Click and hold to talk again.");
      });
  }

  function playBase64Audio(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => {
      URL.revokeObjectURL(url);
      setStatus("Click and hold to talk again.");
    };
    audio.onerror = () => {
      setStatus("Playback error.");
      URL.revokeObjectURL(url);
    };
    audio.play();
  }

  recordBtn.addEventListener("mousedown", startRecording);
  recordBtn.addEventListener("mouseup", stopRecording);
  recordBtn.addEventListener("mouseleave", stopRecording);
  recordBtn.addEventListener("touchstart", (e) => {
    e.preventDefault();
    startRecording();
  });
  recordBtn.addEventListener("touchend", (e) => {
    e.preventDefault();
    stopRecording();
  });
})();
