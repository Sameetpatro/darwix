/**
 * Crestview Financial - AI Voice Softphone Client
 * Connects Web Speech ASR -> Backend DeepSeek LLM -> Edge-TTS Audio Playback
 */

// DOM Elements
const btnCall = document.getElementById("btn-call");
const btnHangup = document.getElementById("btn-hangup");
const btnMic = document.getElementById("btn-mic");
const micText = document.getElementById("mic-text");
const callTimerDisplay = document.getElementById("call-timer");
const callTimerDot = document.getElementById("call-timer-dot");
const callStatusLabel = document.getElementById("call-status-label");
const subStatusLabel = document.getElementById("sub-status-label");
const avatarRing = document.getElementById("avatar-ring");
const activeCallIdEl = document.getElementById("active-call-id");
const messagesContainer = document.getElementById("messages-container");
const emptyTranscript = document.getElementById("empty-transcript");
const agentAudio = document.getElementById("agent-audio-player");
const btnExport = document.getElementById("btn-download-transcript");
const btnRefreshHistory = document.getElementById("btn-refresh-history");
const historyTableBody = document.getElementById("history-table-body");
const noticeBanner = document.getElementById("notice-banner");
const noticeMessage = document.getElementById("notice-message");

// Fallback Text Input
const textForm = document.getElementById("text-speech-form");
const manualInput = document.getElementById("manual-text-input");
const btnManualSend = document.getElementById("btn-manual-send");

// Latency HUD
const hudAsr = document.getElementById("hud-asr");
const hudLlm = document.getElementById("hud-llm");
const hudTts = document.getElementById("hud-tts");
const hudTotal = document.getElementById("hud-total");

// Qualification Dashboard Elements (Part 2)
const qualificationBadge = document.getElementById("qualification-badge");
const qualProgressText = document.getElementById("qualification-progress-text");
const qualProgressFill = document.getElementById("qualification-progress-fill");
const qualAlert = document.getElementById("qualification-alert");
const qualAlertText = document.getElementById("qualification-alert-text");

const SLOT_FIELDS = [
  "customer_name", "business_name", "business_type", "business_age",
  "monthly_revenue", "requested_amount", "loan_purpose", "existing_loans", "location"
];

function resetQualificationUI() {
  if (!qualificationBadge) return;
  qualificationBadge.className = "decision-pill";
  qualificationBadge.textContent = "Collecting (0/9)";
  if (qualProgressText) qualProgressText.textContent = "0%";
  if (qualProgressFill) qualProgressFill.style.width = "0%";
  if (qualAlert) qualAlert.classList.add("hidden");

  SLOT_FIELDS.forEach(field => {
    const item = document.getElementById(`slot-${field}`);
    const val = document.getElementById(`val-${field}`);
    if (item) {
      item.classList.remove("filled");
      const icon = item.querySelector(".slot-status-icon");
      if (icon) icon.innerHTML = "&#9675;";
    }
    if (val) val.textContent = "Pending...";
  });
}

function updateQualificationUI(qual, dialogAction) {
  if (!qual) return;

  const count = qual.collected_count || 0;
  const pct = Math.round((count / 9) * 100);

  if (qualProgressText) qualProgressText.textContent = `${pct}%`;
  if (qualProgressFill) qualProgressFill.style.width = `${pct}%`;

  if (qualificationBadge) {
    qualificationBadge.className = "decision-pill";
    if (qual.is_escalated) {
      qualificationBadge.classList.add("escalated");
      qualificationBadge.textContent = "Escalated";
    } else if (count === 9) {
      if (dialogAction === "underwriting_decision") {
        qualificationBadge.classList.add("pre-qualified");
        qualificationBadge.textContent = "Decision Ready";
      } else {
        qualificationBadge.textContent = "Confirming";
      }
    } else {
      qualificationBadge.textContent = `Collecting (${count}/9)`;
    }
  }

  SLOT_FIELDS.forEach(field => {
    const item = document.getElementById(`slot-${field}`);
    const valEl = document.getElementById(`val-${field}`);
    const value = qual[field];

    if (item && valEl) {
      if (value && value !== "None" && !String(value).toLowerCase().includes("pending")) {
        item.classList.add("filled");
        const icon = item.querySelector(".slot-status-icon");
        if (icon) icon.innerHTML = "&#10003;";
        valEl.textContent = value;
      }
    }
  });

  if (qualAlert && qualAlertText) {
    if (dialogAction === "resolve_conflict") {
      qualAlert.classList.remove("hidden");
      qualAlertText.textContent = "Discrepancy detected. Clarifying with caller...";
    } else if (dialogAction === "escalate") {
      qualAlert.classList.remove("hidden");
      qualAlertText.textContent = "Transferred to senior human advisor.";
    } else {
      qualAlert.classList.add("hidden");
    }
  }
}

// Canvas Visualizer
const canvas = document.getElementById("waveform-canvas");
const ctx = canvas ? canvas.getContext("2d") : null;

// Application State
let isCallActive = false;
let currentCallId = null;
let callStartTime = null;
let timerInterval = null;
let speechRecognition = null;
let isSpeaking = false; // Agent is playing audio
let isListening = false;
let userSpeechStartTime = null;
let audioContext = null;
let analyser = null;
let visualizerAnimationId = null;

// Check SpeechRecognition Support
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

// 1. Health & Configuration Check
async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    if (res.ok) {
      const data = await res.json();
      const llmInfo = data.providers?.llm;
      if (llmInfo?.last_error && llmInfo.last_error.includes("Insufficient Balance")) {
        noticeBanner.classList.remove("hidden");
        noticeMessage.textContent =
          "DeepSeek API reports Insufficient Balance. Voice Pipeline is running in smart fallback mode with Edge-TTS and full speech loop.";
      }
    }
  } catch (err) {
    console.warn("Health check error:", err);
  }
}

// 2. Waveform Visualizer
function setupVisualizer() {
  if (!canvas || !ctx) return;

  let phase = 0;
  function draw() {
    visualizerAnimationId = requestAnimationFrame(draw);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const centerY = canvas.height / 2;
    const width = canvas.width;

    ctx.beginPath();
    ctx.lineWidth = 2;

    if (isSpeaking) {
      ctx.strokeStyle = "#06b6d4"; // Cyan for agent speaking
      for (let x = 0; x < width; x++) {
        const y = centerY + Math.sin(x * 0.05 + phase) * 14 * Math.sin(x * 0.02 + phase * 0.5);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      phase += 0.15;
    } else if (isListening) {
      ctx.strokeStyle = "#10b981"; // Green for customer listening
      for (let x = 0; x < width; x++) {
        const y = centerY + Math.sin(x * 0.08 + phase) * 8 * Math.cos(x * 0.03);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      phase += 0.1;
    } else {
      ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
      ctx.moveTo(0, centerY);
      ctx.lineTo(width, centerY);
    }

    ctx.stroke();
  }
  draw();
}

// 3. Call Timer
function startTimer() {
  callStartTime = Date.now();
  callTimerDot.classList.add("active");
  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
    const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const secs = String(elapsed % 60).padStart(2, "0");
    callTimerDisplay.textContent = `${mins}:${secs}`;
  }, 1000);
}

function stopTimer() {
  clearInterval(timerInterval);
  callTimerDot.classList.remove("active");
  callTimerDisplay.textContent = "00:00";
}

// 4. Speech Recognition (ASR)
function initSpeechRecognition() {
  if (!SpeechRecognition) {
    console.warn("Web Speech API not supported in this browser.");
    subStatusLabel.textContent = "Browser speech recognition unavailable. Use text bar below.";
    return;
  }

  speechRecognition = new SpeechRecognition();
  speechRecognition.continuous = true;
  speechRecognition.interimResults = false;
  speechRecognition.lang = currentMarket === "id" ? "id-ID" : "en-US";

  speechRecognition.onstart = () => {
    isListening = true;
    micText.textContent = "Listening...";
    subStatusLabel.textContent = "Listening to you... Speak into your microphone.";
    avatarRing.classList.add("listening");
    userSpeechStartTime = performance.now();
  };

  speechRecognition.onresult = (event) => {
    if (isSpeaking) return; // Ignore audio echo when agent speaks
    const lastResult = event.results[event.results.length - 1];
    if (lastResult.isFinal) {
      const transcript = lastResult[0].transcript.trim();
      const confidence = lastResult[0].confidence;
      const durationMs = userSpeechStartTime ? performance.now() - userSpeechStartTime : 0;
      if (transcript.length > 0) {
        handleUserSpeechTurn(transcript, durationMs, confidence);
      }
    }
  };

  speechRecognition.onerror = (event) => {
    console.warn("[ASR] Recognition error:", event.error);
    if (event.error === "not-allowed") {
      subStatusLabel.textContent = "Microphone access blocked. Please enable mic permissions or type below.";
    }
  };

  speechRecognition.onend = () => {
    isListening = false;
    avatarRing.classList.remove("listening");
    if (isCallActive && !isSpeaking) {
      // Auto restart listening if still in active call
      try {
        speechRecognition.start();
      } catch (e) {}
    }
  };
}

function startListening() {
  if (speechRecognition && isCallActive && !isSpeaking) {
    try {
      speechRecognition.start();
    } catch (e) {
      // Recognition might already be running
    }
  }
}

function stopListening() {
  if (speechRecognition) {
    try {
      speechRecognition.stop();
    } catch (e) {}
  }
  isListening = false;
  avatarRing.classList.remove("listening");
}

// 5. Audio Playback (TTS)
function playAgentAudio(audioUrl) {
  if (!audioUrl) return;

  isSpeaking = true;
  stopListening();

  callStatusLabel.textContent = "Vani Speaking...";
  subStatusLabel.textContent = "Playing neural voice response";
  avatarRing.className = "agent-avatar-ring speaking";

  agentAudio.src = audioUrl;
  agentAudio.play().catch((err) => {
    console.warn("Audio autoplay blocked by browser policy, click to play:", err);
    callStatusLabel.textContent = "Audio ready (Click to play)";
  });

  agentAudio.onended = () => {
    isSpeaking = false;
    avatarRing.className = "agent-avatar-ring";
    if (isCallActive) {
      callStatusLabel.textContent = "Call Connected";
      subStatusLabel.textContent = "Your turn to speak...";
      startListening();
    }
  };
}

// 6. UI Renderers
function appendTurn(speaker, text, audioUrl, latencies, kbCitation) {
  if (emptyTranscript) emptyTranscript.style.display = "none";

  const turnEl = document.createElement("div");
  turnEl.className = `chat-turn ${speaker}`;

  const header = document.createElement("div");
  header.className = "turn-header";
  header.innerHTML = `<span class="turn-speaker-badge">${speaker === "agent" ? "Vani (Agent)" : "You (Caller)"}</span>`;

  const bubble = document.createElement("div");
  bubble.className = "turn-bubble";
  bubble.textContent = text;

  const footer = document.createElement("div");
  footer.className = "turn-footer";

  if (latencies && latencies.total_roundtrip_ms > 0) {
    const latencySpan = document.createElement("span");
    latencySpan.className = "turn-latency";
    latencySpan.textContent = `Latency: ${latencies.total_roundtrip_ms.toFixed(0)}ms`;
    footer.appendChild(latencySpan);
  }

  if (audioUrl) {
    const playBtn = document.createElement("button");
    playBtn.className = "play-turn-btn";
    playBtn.innerHTML = "&#9658; Replay Audio";
    playBtn.onclick = () => {
      const sound = new Audio(audioUrl);
      sound.play();
    };
    footer.appendChild(playBtn);
  }

  turnEl.appendChild(header);
  turnEl.appendChild(bubble);

  if (kbCitation) {
    const citationBadge = document.createElement("div");
    citationBadge.className = "kb-citation-badge";
    citationBadge.innerHTML = `<span class="kb-icon">&#128214;</span> <span>Source: ${kbCitation}</span>`;
    turnEl.appendChild(citationBadge);
  }

  turnEl.appendChild(footer);

  messagesContainer.appendChild(turnEl);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function updateLatencyHud(latencies) {
  if (!latencies) return;
  hudAsr.textContent = latencies.asr_ms ? `${latencies.asr_ms.toFixed(0)} ms` : "0 ms";
  hudLlm.textContent = latencies.llm_ms ? `${latencies.llm_ms.toFixed(0)} ms` : "0 ms";
  hudTts.textContent = latencies.tts_ms ? `${latencies.tts_ms.toFixed(0)} ms` : "0 ms";
  hudTotal.textContent = latencies.total_roundtrip_ms ? `${latencies.total_roundtrip_ms.toFixed(0)} ms` : "0 ms";
}

// 7. Core Call Actions
// 7. Core Call Actions
async function startCall() {
  btnCall.classList.add("hidden");
  btnHangup.classList.remove("hidden");
  callStatusLabel.textContent = "Connecting...";
  subStatusLabel.textContent = "Connecting to Vani...";

  try {
    const res = await fetch("/api/call/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ caller_id: "web_client" }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    currentCallId = data.call_id;
    isCallActive = true;

    activeCallIdEl.textContent = currentCallId;
    btnExport.disabled = false;
    manualInput.disabled = false;
    btnManualSend.disabled = false;

    startTimer();
    callStatusLabel.textContent = "Call Connected";

    // Reset & Initialize Qualification Dashboard
    resetQualificationUI();
    if (data.qualification) {
      updateQualificationUI(data.qualification, data.dialog_action);
    }

    // Append initial greeting
    appendTurn("agent", data.agent_text, data.audio_url, data.latencies);
    updateLatencyHud(data.latencies);

    // Play agent voice greeting
    if (data.audio_url) {
      playAgentAudio(data.audio_url);
    } else {
      startListening();
    }
  } catch (err) {
    console.error("Start call failed:", err);
    callStatusLabel.textContent = "Connection Failed";
    subStatusLabel.textContent = err.message;
    endCall();
  }
}

async function handleUserSpeechTurn(userText, durationMs = 0, confidence = 1.0) {
  if (!isCallActive || !currentCallId) return;

  // Append user message immediately
  appendTurn("customer", userText, null, null);

  callStatusLabel.textContent = "Analyzing intent...";
  subStatusLabel.textContent = "Autonomous language, intent & domain reasoning...";
  avatarRing.className = "agent-avatar-ring";

  try {
    const res = await fetch("/api/call/turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        call_id: currentCallId,
        user_text: userText,
        client_asr_duration_ms: durationMs,
        confidence: confidence,
      }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();

    // Adapt speech recognition language for subsequent mic input
    if (speechRecognition && data.language) {
      if (data.language === "id") {
        speechRecognition.lang = "id-ID";
      } else if (data.language === "tl") {
        speechRecognition.lang = "fil-PH";
      } else {
        speechRecognition.lang = "en-US";
      }
    }

    // Update Qualification Checklist in real-time if available
    if (data.qualification) {
      updateQualificationUI(data.qualification, data.dialog_action);
    }

    // Append agent message, citation, and update metrics
    appendTurn("agent", data.agent_text, data.audio_url, data.latencies, data.kb_citation);
    updateLatencyHud(data.latencies);

    // Play synthesized voice
    if (data.audio_url) {
      playAgentAudio(data.audio_url);
    }
  } catch (err) {
    console.error("Turn processing error:", err);
    callStatusLabel.textContent = "Error in turn";
    subStatusLabel.textContent = err.message;
    startListening();
  }
}

async function endCall() {
  if (!isCallActive && !currentCallId) return;

  isCallActive = false;
  stopTimer();
  stopListening();

  if (agentAudio) {
    agentAudio.pause();
    agentAudio.currentTime = 0;
  }

  btnHangup.classList.add("hidden");
  btnCall.classList.remove("hidden");
  callStatusLabel.textContent = "Call Ended";
  subStatusLabel.textContent = "Call transcript saved to disk.";
  avatarRing.className = "agent-avatar-ring";
  manualInput.disabled = true;
  btnManualSend.disabled = true;

  try {
    if (currentCallId) {
      await fetch("/api/call/end", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ call_id: currentCallId, reason: "user_hangup" }),
      });
      loadCallHistory();
    }
  } catch (err) {
    console.warn("End call notification error:", err);
  }
}

// 8. History & Export
async function loadCallHistory() {
  try {
    const res = await fetch("/api/calls");
    if (!res.ok) return;
    const data = await res.json();
    const calls = data.calls || [];

    if (calls.length === 0) {
      historyTableBody.innerHTML = `<tr><td colspan="7" class="text-center">No completed calls yet. Make your first test call above!</td></tr>`;
      return;
    }

    historyTableBody.innerHTML = calls
      .map(
        (c) => `
      <tr>
        <td><strong>${c.call_id}</strong></td>
        <td><span class="status-pill">${c.status}</span></td>
        <td>${c.total_turns}</td>
        <td>${c.avg_roundtrip_latency_ms} ms</td>
        <td>${c.avg_llm_latency_ms} ms</td>
        <td>${c.avg_tts_latency_ms} ms</td>
        <td>
          <a href="/api/call/${c.call_id}/transcript" target="_blank" class="btn-sm" style="text-decoration:none;">View JSON</a>
        </td>
      </tr>
    `
      )
      .join("");
  } catch (err) {
    console.warn("Could not load call history:", err);
  }
}

function exportTranscript() {
  if (!currentCallId) return;
  window.open(`/api/call/${currentCallId}/transcript`, "_blank");
}

// 9. Event Listeners
btnCall.addEventListener("click", startCall);
btnHangup.addEventListener("click", endCall);
btnExport.addEventListener("click", exportTranscript);
btnRefreshHistory.addEventListener("click", loadCallHistory);

textForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const val = manualInput.value.trim();
  if (val) {
    manualInput.value = "";
    handleUserSpeechTurn(val, 0, 1.0);
  }
});

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  initSpeechRecognition();
  setupVisualizer();
  loadCallHistory();
});
