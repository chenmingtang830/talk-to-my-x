// X-LiveCast voice room client (Gemini Live API).
// Runs locally: the browser connects directly to the Gemini Live WebSocket with
// the user's own API key (served from the local server over localhost).
// Audio: input raw PCM16 @ 16 kHz, output PCM16 @ 24 kHz. Barge-in is signaled
// by the server via serverContent.interrupted.

const INPUT_RATE = 16000;   // Gemini Live expects 16 kHz PCM input
const OUTPUT_RATE = 24000;  // Gemini Live sends 24 kHz PCM output

const els = {
  status: document.getElementById("status"),
  orb: document.getElementById("orb"),
  orbIcon: document.getElementById("orbIcon"),
  orbLabel: document.getElementById("orbLabel"),
  captions: document.getElementById("captions"),
  briefPanel: document.getElementById("briefPanel"),
  briefText: document.getElementById("briefText"),
  muteBtn: document.getElementById("muteBtn"),
  stopBtn: document.getElementById("stopBtn"),
  replayBack: document.getElementById("replayBack"),
  replayFwd: document.getElementById("replayFwd"),
};

const state = {
  phase: "idle", // idle | connecting | live | paused | error — drives the orb button
  ws: null,
  ctx: null,
  micStream: null,
  micNode: null,
  micSource: null,
  muted: false,
  paused: false,
  playHead: 0,
  activeSources: [],
  hostLineEl: null,
  userLineEl: null,
  pendingHostText: "",
  brief: "",
  briefItems: [], // structured grounding: [{topic, summary, sources:[{author,id,url}]}]
  model: "",
  voice: "Puck",
  // Session capture: the full record of this conversation (turns + tool
  // calls), flushed to the server when the user ends the session. This is
  // what a "recap draft" (Phase D) gets generated from later.
  sessionEvents: [],
  startedAt: null,
  // Brief replay: while the host reads the initial brief, we also capture the
  // raw audio into a seekable buffer so it can be replayed with the ±5s
  // buttons (separate from the live realtime playback path, which can't be
  // seeked — it has no fixed length and can be interrupted at any point).
  briefCapturing: false,
  briefChunks: [],
  briefBuffer: null,
  replaySource: null,
  replayStartedAt: 0,
  replayOffset: 0,
  replayPlaying: false,
};

function logEvent(type, data) {
  state.sessionEvents.push({ type, at: new Date().toISOString(), ...data });
}

function setStatus(text, kind) {
  els.status.textContent = text;
  els.status.className = `status status--${kind}`;
}

function setOrb(mode) {
  els.orb.classList.toggle("is-speaking", mode === "speaking");
  els.orb.classList.toggle("is-listening", mode === "listening");
}

// The orb doubles as the single Start/Pause/Resume control — one button
// instead of three overlapping ones. `setPhase` is the only place that
// changes its icon/label and enables the Mute/End buttons.
const PHASES = {
  idle: { status: "idle", kind: "idle", icon: "▶", label: "Tap to start" },
  connecting: { status: "connecting", kind: "connecting", icon: "…", label: "Connecting…" },
  live: { status: "live", kind: "live", icon: "⏸", label: "Tap to pause" },
  paused: { status: "paused", kind: "idle", icon: "▶", label: "Tap to resume" },
  error: { status: "error", kind: "error", icon: "!", label: "Tap to retry" },
};

function setPhase(phase) {
  state.phase = phase;
  const cfg = PHASES[phase] || PHASES.idle;
  setStatus(cfg.status, cfg.kind);
  els.orbIcon.textContent = cfg.icon;
  els.orbLabel.textContent = cfg.label;
  const active = phase === "live" || phase === "paused";
  els.muteBtn.disabled = !active;
  els.stopBtn.disabled = !active;
}

// ---------- PCM helpers ----------

function float32ToBase64PCM16(float32) {
  const pcm16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  const bytes = new Uint8Array(pcm16.buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function base64PCM16ToFloat32(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const pcm16 = new Int16Array(bytes.buffer);
  const float32 = new Float32Array(pcm16.length);
  for (let i = 0; i < pcm16.length; i++) float32[i] = pcm16[i] / 32768;
  return float32;
}

// ---------- Playback ----------

function playChunk(float32) {
  // Keep scheduling even while paused: the AudioContext is suspended, so these
  // queue up and play seamlessly on resume (continuing mid-sentence).
  if (!state.ctx) return;
  if (state.briefCapturing) state.briefChunks.push(float32);
  // Declare the buffer's own 24 kHz rate; the AudioContext resamples on play.
  const buffer = state.ctx.createBuffer(1, float32.length, OUTPUT_RATE);
  buffer.copyToChannel(float32, 0);
  const source = state.ctx.createBufferSource();
  source.buffer = buffer;
  source.connect(state.ctx.destination);

  const now = state.ctx.currentTime;
  const startAt = Math.max(now, state.playHead);
  source.start(startAt);
  state.playHead = startAt + buffer.duration;

  state.activeSources.push(source);
  source.onended = () => {
    state.activeSources = state.activeSources.filter((s) => s !== source);
    if (state.activeSources.length === 0) setOrb("idle");
  };
  setOrb("speaking");
}

function stopPlayback() {
  for (const s of state.activeSources) {
    try { s.stop(); } catch (_) { /* already stopped */ }
  }
  state.activeSources = [];
  state.playHead = state.ctx ? state.ctx.currentTime : 0;
  setOrb("idle");
}

// ---------- Brief replay (±5s buttons beside the orb, intro reading only) ----------
// Scope: this only replays the recorded INTRO reading, not the live, open-ended
// conversation (which has no fixed length and can't be pre-recorded/seeked).

function finalizeBriefCapture() {
  if (!state.briefCapturing) return;
  state.briefCapturing = false;
  if (state.briefChunks.length === 0 || !state.ctx) return;

  const totalLen = state.briefChunks.reduce((n, c) => n + c.length, 0);
  const combined = new Float32Array(totalLen);
  let offset = 0;
  for (const chunk of state.briefChunks) { combined.set(chunk, offset); offset += chunk.length; }
  state.briefChunks = [];

  const buffer = state.ctx.createBuffer(1, combined.length, OUTPUT_RATE);
  buffer.copyToChannel(combined, 0);
  state.briefBuffer = buffer;
  state.replayOffset = 0;
  updateReplayButtons();
}

function replayStop() {
  if (state.replaySource) {
    try { state.replaySource.onended = null; state.replaySource.stop(); } catch (_) { /* already stopped */ }
    state.replaySource = null;
  }
  state.replayPlaying = false;
}

function replayCurrentTime() {
  if (!state.briefBuffer) return 0;
  if (state.replayPlaying) {
    return Math.min(state.replayOffset + (state.ctx.currentTime - state.replayStartedAt), state.briefBuffer.duration);
  }
  return state.replayOffset;
}

function replayPlayFrom(offsetSec) {
  if (!state.briefBuffer || !state.ctx) return;
  replayStop();
  const clamped = Math.max(0, Math.min(offsetSec, Math.max(0, state.briefBuffer.duration - 0.02)));
  const source = state.ctx.createBufferSource();
  source.buffer = state.briefBuffer;
  source.connect(state.ctx.destination);
  source.start(0, clamped);
  state.replaySource = source;
  state.replayOffset = clamped;
  state.replayStartedAt = state.ctx.currentTime;
  state.replayPlaying = true;
  source.onended = () => {
    if (state.replaySource === source) {
      state.replayPlaying = false;
      state.replaySource = null;
      state.replayOffset = state.briefBuffer.duration;
    }
  };
}

function replaySkip(deltaSec) {
  // Tapping either button always (re)starts playback from the shifted
  // position — no separate play/pause needed for this secondary control.
  if (!state.briefBuffer) return;
  replayPlayFrom(replayCurrentTime() + deltaSec);
}

function updateReplayButtons() {
  // The whole AudioContext is suspended while the main session is paused, so
  // replay (which shares state.ctx) can't produce sound either — disable
  // visibly instead of letting taps silently do nothing.
  const disabled = state.paused || !state.briefBuffer;
  els.replayBack.disabled = disabled;
  els.replayFwd.disabled = disabled;
}

// ---------- Captions ----------

function addLine(who, cls) {
  const p = document.createElement("p");
  p.className = `line line--${cls}`;
  const label = document.createElement("span");
  label.className = "line__who";
  label.textContent = who + " ";
  const span = document.createElement("span");
  p.append(label, span);
  els.captions.append(p);
  els.captions.scrollTop = els.captions.scrollHeight;
  return span;
}

function flushUserTurn() {
  if (state.userLineEl && state.userLineEl.textContent.trim()) {
    logEvent("user", { text: state.userLineEl.textContent.trim() });
  }
}

function flushHostTurn() {
  // Include any text still buffered from a pause — the model said it even if
  // the UI hadn't displayed it yet.
  const text = ((state.hostLineEl ? state.hostLineEl.textContent : "") + state.pendingHostText).trim();
  if (text) logEvent("host", { text });
}

function appendHost(text) {
  // Host is speaking → the user's turn is over; start a fresh user line next time.
  flushUserTurn();
  state.userLineEl = null;
  if (!state.hostLineEl) state.hostLineEl = addLine("Host", "host");
  state.hostLineEl.textContent += text;
  els.captions.scrollTop = els.captions.scrollHeight;
}

function appendUser(text) {
  if (!state.userLineEl) state.userLineEl = addLine("You", "you");
  state.userLineEl.textContent += text;
  els.captions.scrollTop = els.captions.scrollHeight;
}

// ---------- Gemini Live protocol ----------

function send(obj) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify(obj));
  }
}

const TOOL_DECLARATIONS = [
  {
    name: "search_x",
    description:
      "Search recent X (Twitter) posts from the last 7 days. Use this when the " +
      "user asks about the latest on a topic, what people are saying, or trends.",
    parameters: {
      type: "object",
      properties: {
        query: { type: "string", description: "Search query, e.g. 'AI voice agents'." },
        limit: { type: "number", description: "How many posts to return (1-25)." },
      },
      required: ["query"],
    },
  },
  {
    name: "get_home_timeline",
    description:
      "Get the user's own X home timeline (reverse-chronological recent posts " +
      "from accounts they follow). Use to pull what's new in their feed.",
    parameters: {
      type: "object",
      properties: {
        limit: { type: "number", description: "How many posts to return (1-25)." },
      },
    },
  },
  {
    name: "get_user_posts",
    description:
      "Get a specific X user's recent posts by @handle. Use when the user asks " +
      "what someone specific has been posting.",
    parameters: {
      type: "object",
      properties: {
        username: { type: "string", description: "X handle, with or without the @, e.g. 'AnthropicAI'." },
        limit: { type: "number", description: "How many posts to return (1-25)." },
      },
      required: ["username"],
    },
  },
  {
    name: "read_url",
    description:
      "Fetch a web page and read its article text — use when a post links to an " +
      "article/blog and the user wants to know what it actually says, not just " +
      "the post text. Pass the link exactly as it appears in the post (t.co " +
      "short links are followed automatically). Works best on standard articles; " +
      "heavily JS-rendered sites may return little text.",
    parameters: {
      type: "object",
      properties: {
        url: { type: "string", description: "The URL to fetch, e.g. a t.co link from a post's text." },
      },
      required: ["url"],
    },
  },
];

function buildGroundingBlock() {
  if (!state.briefItems.length) return "";
  const lines = state.briefItems.map((item) => {
    const sources = (item.sources || []).map((s) => {
      if (typeof s === "string") return s; // legacy: bare handle, no link
      const handle = s.author ? `@${s.author}` : "";
      return s.url ? `${handle} (${s.url})` : handle;
    }).filter(Boolean).join(", ");
    return `- ${item.topic}: ${item.summary}` + (sources ? `\n  sources: ${sources}` : "");
  });
  return "\n\n=== GROUNDING (exact sources behind the briefing) ===\n" + lines.join("\n");
}

function sendSetup() {
  const grounding = buildGroundingBlock();
  const instructions =
    "You are the friendly host of a personal morning X briefing. " +
    "Keep it conversational and concise. Start by reading the user's briefing " +
    "below in a natural, spoken way, then invite them to interrupt with " +
    "questions. You have tools to pull live X data: use search_x for topics, " +
    "get_home_timeline for the user's feed, get_user_posts when they ask what a " +
    "specific person has posted, and read_url when a post links to an article " +
    "and the user wants to know what it says (pass the link found in the post's " +
    "text). Call them when the user wants the latest, and summarize results " +
    "naturally (mention who posted). If a tool " +
    "returns an error, tell the user X isn't connected yet and continue." +
    (grounding
      ? " IMPORTANT: when the user asks about something specific mentioned in " +
        "the briefing (a person, claim, or event), first check the GROUNDING " +
        "section below for the exact source post — it's the real material the " +
        "briefing was built from. Prefer quoting/using that directly (read_url " +
        "on its link if they want more) over a broad search or pulling someone's " +
        "whole post history, which is less precise."
      : "") +
    " If the user says 'wrap up' or 'that's it', give a one-line closing." +
    "\n\n=== TODAY'S BRIEFING ===\n" + state.brief +
    grounding;

  send({
    setup: {
      model: `models/${state.model}`,
      generationConfig: {
        responseModalities: ["AUDIO"],
        speechConfig: {
          voiceConfig: { prebuiltVoiceConfig: { voiceName: state.voice } },
        },
      },
      systemInstruction: { parts: [{ text: instructions }] },
      tools: [{ functionDeclarations: TOOL_DECLARATIONS }],
      outputAudioTranscription: {},
      inputAudioTranscription: {},
    },
  });
}

function kickOff() {
  state.briefCapturing = true;
  state.briefChunks = [];
  send({
    clientContent: {
      turns: [{ role: "user", parts: [{ text: "Please start my morning briefing now." }] }],
      turnComplete: true,
    },
  });
}

function handleServerContent(sc) {
  if (sc.interrupted) {
    // Barge-in: user spoke, model yielded. Flush queued audio immediately.
    stopPlayback();
    state.hostLineEl = null;
    setStatus("listening", "listening");
    setOrb("listening");
    return;
  }

  const parts = sc.modelTurn && sc.modelTurn.parts;
  if (parts) {
    for (const part of parts) {
      const inline = part.inlineData || part.inline_data;
      if (inline && inline.data) playChunk(base64PCM16ToFloat32(inline.data));
    }
  }

  if (sc.inputTranscription && sc.inputTranscription.text) {
    // Some barge-ins don't come with an explicit `interrupted` flag — e.g. if
    // the previous turn had already completed server-side and only the
    // client's own scheduled-ahead audio was still catching up. Stop any
    // lingering audio the instant real user speech is detected, so playback
    // and the model's reaction (captions, tool calls) never conflict.
    stopPlayback();
    state.hostLineEl = null;
    appendUser(sc.inputTranscription.text);
    setStatus("listening", "listening");
  }
  if (sc.outputTranscription && sc.outputTranscription.text) {
    // While paused, buffer caption text instead of streaming it — otherwise
    // captions race ahead of the frozen audio and look out of sync on resume.
    if (state.paused) {
      state.pendingHostText += sc.outputTranscription.text;
    } else {
      appendHost(sc.outputTranscription.text);
      setStatus("live", "live");
    }
  }
  if (sc.turnComplete) {
    flushHostTurn();
    flushUserTurn();
    state.hostLineEl = null;
    state.userLineEl = null;
    state.pendingHostText = "";
    finalizeBriefCapture();
  }
}

function addToolResultLine(name, args, result) {
  const p = document.createElement("p");
  p.className = "line line--tool";

  const label = document.createElement("span");
  label.className = "line__who";
  label.textContent = "🔧 " + name;
  p.appendChild(label);

  const argsText = Object.values(args || {}).filter((v) => v !== undefined && v !== "").join(", ");
  if (argsText) {
    const argsSpan = document.createElement("span");
    argsSpan.className = "line__tool-args";
    argsSpan.textContent = " " + argsText;
    p.appendChild(argsSpan);
  }

  const list = document.createElement("ul");
  list.className = "tool-results";

  if (result && result.error) {
    const li = document.createElement("li");
    li.className = "tool-results__error";
    li.textContent = result.error;
    list.appendChild(li);
  } else if (name === "read_url") {
    // Shape: { url, final_url, title, text, truncated } — one fetched page.
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = (result && (result.final_url || result.url)) || "#";
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = (result && result.title) || (result && result.url) || "(page)";
    li.appendChild(a);
    if (result && result.text) {
      const preview = document.createElement("div");
      preview.className = "tool-results__preview";
      preview.textContent = result.text.slice(0, 220) + (result.truncated ? "…" : "");
      li.appendChild(preview);
    }
    list.appendChild(li);
  } else {
    const items = (result && result.results) || [];
    if (items.length === 0) {
      const li = document.createElement("li");
      li.textContent = "(no results)";
      list.appendChild(li);
    }
    for (const item of items.slice(0, 8)) {
      const li = document.createElement("li");
      const snippet = (item.text || "").slice(0, 100);
      if (item.url) {
        const a = document.createElement("a");
        a.href = item.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = `@${item.author}: ${snippet}`;
        li.appendChild(a);
      } else {
        li.textContent = `@${item.author}: ${snippet}`;
      }
      list.appendChild(li);
    }
  }
  p.appendChild(list);
  els.captions.append(p);
  els.captions.scrollTop = els.captions.scrollHeight;
}

async function handleToolCall(toolCall) {
  // A tool call is proof the model has moved on to a new response — if any
  // audio from a prior turn is still playing, cut it now rather than let it
  // finish alongside a reaction to something newer (belt-and-braces alongside
  // the inputTranscription-triggered stop above).
  stopPlayback();
  state.hostLineEl = null;

  const calls = toolCall.functionCalls || [];
  const functionResponses = [];
  for (const call of calls) {
    let result;
    try {
      const r = await fetch("/tool", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: call.name, args: call.args || {} }),
      });
      const j = await r.json();
      result = j.result;
    } catch (err) {
      result = { error: String(err) };
    }
    addToolResultLine(call.name, call.args || {}, result);
    functionResponses.push({ id: call.id, name: call.name, response: { result } });
    logEvent("tool_call", { name: call.name, args: call.args || {}, result });
  }
  send({ toolResponse: { functionResponses } });
}

async function handleMessage(raw) {
  // Gemini sends binary (Blob) JSON frames over the socket.
  let text = raw;
  if (raw instanceof Blob) text = await raw.text();
  let msg;
  try { msg = JSON.parse(text); } catch (_) { return; }

  if (msg.setupComplete !== undefined) {
    setPhase("live");
    kickOff();
    return;
  }
  if (msg.toolCall) { handleToolCall(msg.toolCall); return; }
  if (msg.serverContent) handleServerContent(msg.serverContent);
  if (msg.error) {
    console.error("Gemini error", msg.error);
    setStatus("error", "error");
    appendHost(`\n[error] ${msg.error.message || JSON.stringify(msg.error)}`);
  }
}

// ---------- Mic capture ----------

async function startMic() {
  state.micStream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
  });
  state.micSource = state.ctx.createMediaStreamSource(state.micStream);

  // ScriptProcessor is deprecated but universally available and fine for a
  // local demo. It emits Float32 frames at the context rate (16 kHz here).
  state.micNode = state.ctx.createScriptProcessor(4096, 1, 1);
  state.micNode.onaudioprocess = (e) => {
    if (state.muted || state.paused) return;
    const input = e.inputBuffer.getChannelData(0);
    send({
      realtimeInput: {
        audio: { data: float32ToBase64PCM16(input), mimeType: `audio/pcm;rate=${INPUT_RATE}` },
      },
    });
  };

  state.micSource.connect(state.micNode);
  const sink = state.ctx.createGain();
  sink.gain.value = 0;
  state.micNode.connect(sink);
  sink.connect(state.ctx.destination);
}

// ---------- Lifecycle ----------

async function start() {
  setPhase("connecting");
  state.sessionEvents = [];
  state.startedAt = new Date().toISOString();
  // The live transcript now carries the brief's content — the static preview
  // panel would just duplicate it, so hide it for the duration of the call.
  els.briefPanel.classList.add("is-hidden");
  state.briefBuffer = null;
  updateReplayButtons();

  try {
    const [config, brief] = await Promise.all([
      fetch("/config").then((r) => r.json()),
      fetch("/brief").then((r) => r.json()),
    ]);

    if (!config.hasKey || !config.token) {
      const detail = config.error ? `: ${config.error}` : "";
      throw new Error(`Could not get a Gemini session token${detail}. Check GEMINI_API_KEY in .env.`);
    }

    state.model = config.model || "gemini-3.1-flash-live-preview";
    state.voice = config.voice || "Puck";
    state.brief = brief.text || "";
    state.briefItems = brief.items || [];
    els.briefText.textContent = state.brief || "(no brief)";

    // AudioContext at the input rate so mic capture is already 16 kHz.
    state.ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: INPUT_RATE });
    await state.ctx.resume();

    // Constrained endpoint + short-lived ephemeral token — the real API key
    // never reaches the browser (needed once this link can leave the machine).
    const url = `${config.wsBase}?access_token=${encodeURIComponent(config.token)}`;
    state.ws = new WebSocket(url);

    state.ws.onopen = async () => {
      sendSetup();
      await startMic();
      // Phase moves to "live" once setupComplete arrives (see handleMessage) —
      // that's when the model session is actually ready, not just the socket.
    };
    state.ws.onmessage = (m) => { handleMessage(m.data); };
    state.ws.onerror = (e) => {
      console.error("WebSocket error", e);
      setPhase("error");
    };
    state.ws.onclose = () => {
      if (state.phase !== "idle") setPhase("idle");
      setOrb("idle");
    };
  } catch (err) {
    console.error(err);
    setPhase("error");
    appendHost(`\n[error] ${err.message}`);
  }
}

function toggleMute() {
  state.muted = !state.muted;
  els.muteBtn.textContent = state.muted ? "Unmute mic" : "Mute mic";
  els.muteBtn.classList.toggle("is-muted", state.muted);
}

function togglePause() {
  state.paused = !state.paused;
  if (state.paused) {
    // Suspend the whole audio clock: playback freezes mid-sentence and the mic
    // stops. Incoming host audio keeps buffering and resumes seamlessly.
    if (state.ctx) state.ctx.suspend();
    setOrb("idle");
    setPhase("paused");
  } else {
    if (state.ctx) state.ctx.resume();
    if (state.pendingHostText) {
      appendHost(state.pendingHostText);
      state.pendingHostText = "";
    }
    setPhase("live");
  }
  updateReplayButtons();
}

function handleOrbTap() {
  if (state.phase === "connecting") return; // ignore taps mid-connect
  if (state.phase === "idle" || state.phase === "error") {
    start();
  } else {
    togglePause();
  }
}

function endSession() {
  // Capture whatever turn was in progress, then persist the full session so a
  // recap draft can be generated from it later (see SKILL.md recipe).
  flushHostTurn();
  flushUserTurn();
  if (state.sessionEvents.length === 0) return;

  const payload = {
    started_at: state.startedAt,
    ended_at: new Date().toISOString(),
    brief: state.brief,
    model: state.model,
    events: state.sessionEvents,
  };
  // Best-effort; keepalive lets it complete even as the page/connection tears down.
  fetch("/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {});
  state.sessionEvents = [];
}

function stop() {
  endSession();
  if (state.ws) { try { state.ws.close(); } catch (_) {} state.ws = null; }
  stopPlayback();
  replayStop();
  if (state.micNode) { state.micNode.disconnect(); state.micNode.onaudioprocess = null; }
  if (state.micSource) state.micSource.disconnect();
  if (state.micStream) state.micStream.getTracks().forEach((t) => t.stop());
  if (state.ctx) { state.ctx.close(); state.ctx = null; }
  state.paused = false;
  state.briefBuffer = null; // tied to the now-closed AudioContext; next session recaptures
  updateReplayButtons();
  setPhase("idle");
  // Bring back the pre-session preview for the next time you start.
  els.briefPanel.classList.remove("is-hidden");
}

function requestEnd() {
  if (state.phase !== "live" && state.phase !== "paused") return;
  const ok = window.confirm(
    "End this session? A recap of the conversation is saved, and you can start " +
    "a brand new session right after — but this one can't be resumed."
  );
  if (ok) stop();
}

els.orb.addEventListener("click", handleOrbTap);
els.orb.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    handleOrbTap();
  }
});
els.muteBtn.addEventListener("click", toggleMute);
els.stopBtn.addEventListener("click", requestEnd);

els.replayBack.addEventListener("click", () => replaySkip(-5));
els.replayFwd.addEventListener("click", () => replaySkip(5));

setPhase("idle");

// Preload the brief so the panel shows content before starting.
fetch("/brief").then((r) => r.json()).then((b) => {
  state.brief = b.text || "";
  els.briefText.textContent = state.brief || "(no brief)";
}).catch(() => {});
