// X-LiveCast voice room client (Gemini Live API).
// Runs locally: the browser connects directly to the Gemini Live WebSocket with
// the user's own API key (served from the local server over localhost).
// Audio: input raw PCM16 @ 16 kHz, output PCM16 @ 24 kHz. Barge-in is signaled
// by the server via serverContent.interrupted.

const INPUT_RATE = 16000;   // Gemini Live expects 16 kHz PCM input
const OUTPUT_RATE = 24000;  // Gemini Live sends 24 kHz PCM output

const els = {
  status: document.getElementById("status"),
  playBtn: document.getElementById("playBtn"),
  playIcon: document.getElementById("playIcon"),
  playLabel: document.getElementById("playLabel"),
  playHint: document.getElementById("playHint"),
  captions: document.getElementById("captions"),
  briefPanel: document.getElementById("briefPanel"),
  briefText: document.getElementById("briefText"),
  briefSource: document.getElementById("briefSource"),
  briefToast: document.getElementById("briefToast"),
  generateBriefBtn: document.getElementById("generateBriefBtn"),
  muteBtn: document.getElementById("muteBtn"),
  hangupBtn: document.getElementById("hangupBtn"),
  synthBtn: document.getElementById("synthBtn"),
  sessionSelect: document.getElementById("sessionSelect"),
  draftSelect: document.getElementById("draftSelect"),
  newThreadBtn: document.getElementById("newThreadBtn"),
  draftPanel: document.getElementById("draftPanel"),
  draftText: document.getElementById("draftText"),
  draftMeta: document.getElementById("draftMeta"),
  draftResult: document.getElementById("draftResult"),
  copyDraftBtn: document.getElementById("copyDraftBtn"),
  publishBtn: document.getElementById("publishBtn"),
};

const state = {
  phase: "idle", // idle | connecting | live | paused | error | hungup
  ws: null,
  ctx: null,
  micStream: null,
  micNode: null,
  micSource: null,
  muted: false,
  paused: false,
  playHead: 0,
  activeSources: [],
  // Captions: intro is a pre-rendered DM of the spoken script. After that,
  // host/user turns stream into a live bubble so you can read while listening.
  hostBuf: "",
  userBuf: "",
  liveHostEl: null,   // { el, body, p } for the in-progress host reply
  liveUserEl: null,   // { el, body, p } for the in-progress user turn
  hostGapPending: false, // insert a space when continuing after turnComplete
  briefShown: false,
  skipNextHostTranscript: false,
  introStartedAt: 0,
  brief: "",
  briefTitle: "",
  briefItems: [], // structured grounding: [{topic, summary, sources:[{author,name,id,url}]}]
  model: "",
  voice: "Puck",
  // Conversation thread (ChatGPT-style): survives hang-up; Continue Live
  // opens a new Gemini Live socket with this history as context.
  sessionId: null,
  sessionEvents: [],
  startedAt: null,
  connectTimer: null,
  saveTimer: null,
  continuing: false, // true when resuming an existing thread (skip intro read)
  roomToken: "", // from ?token= when XLC_ROOM_TOKEN is set on the host
  draftId: null,
  draftObj: null,
  briefSource: "", // live | sample | file | none
};

// Optional room gate: host sets XLC_ROOM_TOKEN; share URL as https://host/?token=...
(function initRoomToken() {
  try {
    const q = new URLSearchParams(location.search).get("token");
    if (q) {
      state.roomToken = q;
      sessionStorage.setItem("xlc_room_token", q);
    } else {
      state.roomToken = sessionStorage.getItem("xlc_room_token") || "";
    }
  } catch (_) {
    state.roomToken = "";
  }
})();

function apiFetch(path, opts) {
  const options = Object.assign({}, opts || {});
  const headers = Object.assign({}, options.headers || {});
  if (state.roomToken) headers["X-XLC-Token"] = state.roomToken;
  options.headers = headers;
  let url = path;
  if (state.roomToken && !/[?&]token=/.test(path)) {
    url += (path.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(state.roomToken);
  }
  return fetch(url, options);
}

function logEvent(type, data) {
  state.sessionEvents.push({ type, at: new Date().toISOString(), ...data });
  if (typeof scheduleSave === "function") scheduleSave();
}

function setStatus(text, kind) {
  els.status.textContent = text;
  els.status.className = `status status--${kind}`;
}

function setPlayMode(mode) {
  els.playBtn.classList.toggle("is-live", mode === "speaking");
  els.playBtn.classList.toggle("is-listening", mode === "listening");
}

// Call-in control: Start / Pause / Resume / Continue. Hang up keeps the thread.
const PHASES = {
  idle: { status: "idle", kind: "idle", icon: "▶", label: "Start", hint: "Tap Start — live call-in. Hang up anytime; come back to continue." },
  connecting: { status: "connecting", kind: "connecting", icon: "…", label: "Wait", hint: "Connecting…" },
  live: { status: "live", kind: "live", icon: "⏸", label: "Pause", hint: "Live — talk over the host anytime" },
  paused: { status: "paused", kind: "idle", icon: "▶", label: "Resume", hint: "Paused — tap Resume" },
  hungup: { status: "saved", kind: "idle", icon: "▶", label: "Continue", hint: "Thread saved — Continue Live, or Synthesize a post draft" },
  error: { status: "error", kind: "error", icon: "!", label: "Retry", hint: "Something went wrong — tap Retry" },
};

function setPhase(phase) {
  state.phase = phase;
  const cfg = PHASES[phase] || PHASES.idle;
  setStatus(cfg.status, cfg.kind);
  els.playIcon.textContent = cfg.icon;
  els.playLabel.textContent = cfg.label;
  els.playHint.textContent = cfg.hint;
  const onCall = phase === "live" || phase === "paused";
  const hasThread = !!state.sessionId && state.sessionEvents.length > 0;
  els.muteBtn.disabled = !onCall;
  els.hangupBtn.disabled = !onCall;
  els.synthBtn.disabled = !(hasThread || phase === "hungup");
  els.sessionSelect.disabled = onCall || phase === "connecting";
  if (els.draftSelect) els.draftSelect.disabled = onCall || phase === "connecting";
  // Allow New during a live/paused call (it hangs up + resets). Only block while connecting.
  els.newThreadBtn.disabled = phase === "connecting";
  // Generate brief only when not mid-call.
  if (els.generateBriefBtn) {
    els.generateBriefBtn.disabled = onCall || phase === "connecting";
  }
}

function applyBriefPayload(b) {
  state.brief = (b && b.text) || "";
  state.briefItems = (b && b.items) || [];
  state.briefTitle = (b && b.title) || "";
  state.briefSource = (b && b.source) || "";
  if (els.briefText) els.briefText.textContent = state.brief || "(no brief)";
  updateBriefBadge();
}

function updateBriefBadge() {
  if (!els.briefSource) return;
  const src = state.briefSource || "";
  let label = "…";
  let cls = "brief__badge";
  if (src === "live") {
    label = "Live · bookmarks";
    cls += " is-live";
  } else if (src === "sample") {
    label = "Sample brief";
    cls += " is-sample";
  } else if (src === "file") {
    label = "Custom file";
  } else if (src === "none") {
    label = "No brief";
  }
  els.briefSource.textContent = label;
  els.briefSource.className = cls;
}

function setBriefToast(msg, isError) {
  if (!els.briefToast) return;
  els.briefToast.textContent = msg || "";
  els.briefToast.classList.toggle("is-error", !!isError);
}

function formatSessionLabel(s) {
  const title = (s.title || s.id || "Session").trim();
  const when = (s.updated_at || s.started_at || "").replace("T", " ").replace("Z", "").slice(0, 16);
  const n = typeof s.event_count === "number" ? s.event_count : null;
  const parts = [title];
  if (when) parts.push(when);
  if (n != null) parts.push(`${n} turns`);
  if (s.has_draft) parts.push("draft");
  return parts.join(" · ");
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
    if (state.activeSources.length === 0) setPlayMode("idle");
  };
  setPlayMode("speaking");
}

function stopPlayback() {
  for (const s of state.activeSources) {
    try { s.stop(); } catch (_) { /* already stopped */ }
  }
  state.activeSources = [];
  state.playHead = state.ctx ? state.ctx.currentTime : 0;
  setPlayMode("idle");
}

// ---------- Transcript (DM-style: one message = spoken script, inline post links) ----------

function clearThreadHint() {
  const hint = els.captions.querySelector(".thread__hint");
  if (hint) hint.remove();
}

function appendMsg(el) {
  clearThreadHint();
  els.captions.append(el);
  els.captions.scrollTop = els.captions.scrollHeight;
}

function makeMsg(kind, who) {
  const el = document.createElement("article");
  el.className = `msg msg--${kind}`;
  const label = document.createElement("span");
  label.className = "msg__who";
  label.textContent = who;
  const body = document.createElement("div");
  body.className = "msg__body";
  el.append(label, body);
  return { el, body };
}

function addPara(body, text) {
  if (!text) return;
  const p = document.createElement("p");
  p.textContent = text;
  body.appendChild(p);
  return p;
}

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Map of match-key (lowercased handle / display name / alias) → post URL. */
function briefSourceMap() {
  const map = new Map();
  const add = (key, meta) => {
    const k = (key || "").toLowerCase().trim();
    if (k && !map.has(k)) map.set(k, meta);
  };
  for (const item of state.briefItems) {
    for (const src of item.sources || []) {
      if (!src || !src.url) continue;
      const author = src.author ? String(src.author) : "";
      const name = src.name ? String(src.name) : "";
      const meta = { author, name, url: src.url };
      if (author) {
        add(author, meta);
        add(author.replace(/^_+/, ""), meta);
      }
      if (name) {
        add(name, meta);
        const first = name.split(/\s+/)[0];
        if (first && first.length > 2) add(first, meta);
      }
      for (const alias of src.aliases || []) add(String(alias), meta);
    }
  }
  return map;
}

/**
 * Render spoken text into `container`, inserting an inline (post) link right
 * after each mentioned author / alias — so what you read matches what you hear.
 */
function appendTextWithInlinePosts(container, text) {
  const map = briefSourceMap();
  if (!map.size) {
    container.appendChild(document.createTextNode(text));
    return;
  }

  // Longer keys first so multi-word aliases ("Databricks Omnigent") win over
  // single tokens, and `_avichawla` / `avichawla` don't fight oddly.
  const keys = [...new Set(map.keys())].sort((a, b) => b.length - a.length);
  const alt = keys.map((k) => {
    const esc = escapeRegExp(k).replace(/\s+/g, "\\s+");
    // Optional leading @ for handles; multi-word phrases match as-is.
    return k.includes(" ") ? esc : `@?${esc}`;
  }).join("|");
  const re = new RegExp(`(${alt})(?![\\w/])`, "gi");

  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      container.appendChild(document.createTextNode(text.slice(last, m.index)));
    }
    const raw = m[1];
    const key = raw.replace(/^@/, "").toLowerCase().replace(/\s+/g, " ");
    const hit = map.get(key);
    container.appendChild(document.createTextNode(raw));
    if (hit) {
      container.appendChild(document.createTextNode(" ("));
      const a = document.createElement("a");
      a.href = hit.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = "post";
      container.appendChild(a);
      container.appendChild(document.createTextNode(")"));
    }
    last = m.index + raw.length;
  }
  if (last < text.length) {
    container.appendChild(document.createTextNode(text.slice(last)));
  }
}

/** One DM bubble = the spoken script, short paragraphs, posts inline as (post). */
function renderBriefMessage() {
  if (state.briefShown) return;
  state.briefShown = true;

  const { el, body } = makeMsg("host", "Host");
  const script = (state.brief || "").trim();
  if (!script) {
    addPara(body, "(no brief yet)");
    appendMsg(el);
    return;
  }

  for (const para of splitIntoParas(script)) {
    const p = document.createElement("p");
    appendTextWithInlinePosts(p, para);
    body.appendChild(p);
  }
  appendMsg(el);
}

/** Split a finished turn into short paragraphs for quick scanning. */
function splitIntoParas(text) {
  const cleaned = (text || "").replace(/\s+/g, " ").trim();
  if (!cleaned) return [];
  // Prefer natural theme breaks in the spoken script, then sentences.
  const chunks = cleaned
    .split(/(?=\b(?:Second|Third|Fourth|Fifth|Next) theme\b)|(?<=\.)\s+(?=[A-Z])/)
    .map((s) => s.trim())
    .filter(Boolean);

  const paras = [];
  for (const chunk of chunks.length ? chunks : [cleaned]) {
    const sentences = chunk.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [chunk];
    let buf = "";
    for (const s of sentences) {
      const piece = s.trim();
      if (!piece) continue;
      if (!buf) {
        buf = piece;
      } else if ((buf + " " + piece).length <= 200) {
        buf += " " + piece;
      } else {
        paras.push(buf);
        buf = piece;
      }
    }
    if (buf) paras.push(buf);
  }
  return paras;
}

function flushHostTurn() {
  const text = ((state.liveHostEl && state.liveHostEl.p)
    ? state.liveHostEl.p.textContent
    : state.hostBuf).trim();
  state.hostBuf = "";
  state.liveHostEl = null;
  state.hostGapPending = false;
  if (!text) return;
  // Skip dumping the spoken intro as a second bubble — the brief DM already
  // shows the same script with inline (post) links. Later Q&A still shows.
  if (state.skipNextHostTranscript) {
    state.skipNextHostTranscript = false;
    logEvent("host", { text, intro: true });
    return;
  }
  logEvent("host", { text });
}

function flushUserTurn() {
  const text = ((state.liveUserEl && state.liveUserEl.p)
    ? state.liveUserEl.p.textContent
    : state.userBuf).trim();
  state.userBuf = "";
  state.liveUserEl = null;
  if (!text) return;
  logEvent("user", { text });
}

/** Stream host text into one live bubble for the whole reply. */
function appendHostLive(chunk) {
  if (state.skipNextHostTranscript) {
    // Still accumulate for session log, but don't show (intro already rendered).
    state.hostBuf += chunk;
    return;
  }
  flushUserTurn();
  if (!state.liveHostEl) {
    // Reattach to the last Host bubble when it's still the newest message —
    // Gemini often sends `interrupted` between phrases; we must not start a
    // fresh card for each fragment.
    const last = els.captions.lastElementChild;
    if (last && last.classList.contains("msg--host")) {
      const body = last.querySelector(".msg__body") || last;
      let p = body.querySelector("p:last-of-type");
      if (!p) {
        p = document.createElement("p");
        body.appendChild(p);
      }
      state.liveHostEl = { el: last, body, p };
      state.hostGapPending = true;
    } else {
      const { el, body } = makeMsg("host", "Host");
      const p = document.createElement("p");
      body.appendChild(p);
      appendMsg(el);
      state.liveHostEl = { el, body, p };
      state.hostGapPending = false;
    }
  }
  let piece = chunk || "";
  if (state.hostGapPending) {
    state.hostGapPending = false;
    const cur = state.liveHostEl.p.textContent || "";
    if (cur && piece && !/\s$/.test(cur) && !/^\s/.test(piece)) {
      piece = " " + piece;
    }
  }
  state.liveHostEl.p.textContent += piece;
  els.captions.scrollTop = els.captions.scrollHeight;
}

function appendUserLive(chunk) {
  if (!state.liveUserEl) {
    // Starting a user turn → close any open host bubble for logging.
    if (state.liveHostEl) flushHostTurn();
    const { el, body } = makeMsg("you", "You");
    const p = document.createElement("p");
    body.appendChild(p);
    appendMsg(el);
    state.liveUserEl = { el, body, p };
  }
  state.liveUserEl.p.textContent += chunk;
  els.captions.scrollTop = els.captions.scrollHeight;
}

function showError(msg) {
  const { el, body } = makeMsg("error", "Error");
  addPara(body, msg);
  appendMsg(el);
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
    name: "get_post",
    description:
      "Open a specific X post by status URL or tweet id. Returns the post text, " +
      "author display name + handle, and any linked article cards X already " +
      "unwound (title + description). Prefer this when the user asks to open / " +
      "read a post from the briefing. Do NOT use read_url on an x.com status " +
      "URL — those pages are JS shells and usually return nothing. If " +
      "linked_urls has a title/description, summarize from that; only call " +
      "read_url on the article URL if they want the full article body.",
    parameters: {
      type: "object",
      properties: {
        url_or_id: {
          type: "string",
          description: "Tweet id or https://x.com/<user>/status/<id> URL from the GROUNDING section.",
        },
      },
      required: ["url_or_id"],
    },
  },
  {
    name: "get_post_replies",
    description:
      "Pull recent replies in a post's conversation thread (last ~7 days). " +
      "Use when the user asks what people are saying under a post, or wants " +
      "the comment thread. Pass the same status URL / id as get_post. " +
      "Summarize the interesting replies — don't read every one aloud.",
    parameters: {
      type: "object",
      properties: {
        url_or_id: {
          type: "string",
          description: "Tweet id or https://x.com/<user>/status/<id> URL.",
        },
        limit: { type: "number", description: "How many replies to return (1-25)." },
      },
      required: ["url_or_id"],
    },
  },
  {
    name: "read_url",
    description:
      "Fetch a non-X web page (article/blog) and return its readable title/text. " +
      "Use AFTER get_post when the user wants the full article body behind a " +
      "linked_urls entry — pass the article URL (abnormal.ai, etc.), never an " +
      "x.com status URL.",
    parameters: {
      type: "object",
      properties: {
        url: { type: "string", description: "The article URL to fetch (not an x.com status link)." },
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
      const who = s.name || (s.author ? `@${s.author}` : "");
      const handle = s.author ? `@${s.author}` : "";
      const label = s.name && s.author ? `${s.name} (${handle})` : (who || handle);
      return s.url ? `${label} → ${s.url}` : label;
    }).filter(Boolean).join("; ");
    return `- ${item.topic}: ${item.summary}` + (sources ? `\n  sources: ${sources}` : "");
  });
  return "\n\n=== GROUNDING (exact sources behind the briefing) ===\n" + lines.join("\n");
}

function buildHistoryBlock() {
  // Inject prior turns so a new Live socket can continue the same thread.
  // Keep it bounded — last ~30 events, truncate long tool dumps.
  const events = state.sessionEvents.slice(-30);
  if (!events.length) return "";
  const lines = [];
  for (const ev of events) {
    if (ev.type === "user") lines.push(`You: ${(ev.text || "").slice(0, 400)}`);
    else if (ev.type === "host" && !ev.intro) lines.push(`Host: ${(ev.text || "").slice(0, 600)}`);
    else if (ev.type === "tool_call") {
      lines.push(`[looked up ${ev.name}] ${JSON.stringify(ev.args || {}).slice(0, 120)}`);
    }
  }
  if (!lines.length) return "";
  return (
    "\n\n=== PRIOR CONVERSATION ON THIS THREAD ===\n" +
    lines.join("\n") +
    "\n(Continue from here. Do not re-read the briefing unless asked.)"
  );
}

function sendSetup() {
  const grounding = buildGroundingBlock();
  const history = buildHistoryBlock();
  const instructions =
    "You are the friendly host of a personal morning X briefing. " +
    "Keep it conversational and concise. " +
    (history
      ? "This is a CONTINUATION of an existing conversation — greet briefly and wait; do not re-read the whole briefing. "
      : "Start by reading the user's briefing below in a natural, spoken way, then invite them to interrupt with questions. ") +
    "When you mention people, say their display name (e.g. " +
    "'Peter Steinberger'), not their @handle — handles are for links, not speech. " +
    "You have tools to pull live X data: use search_x for topics, " +
    "get_home_timeline for the user's feed, get_user_posts when they ask what a " +
    "specific person has posted, get_post when they want to open a specific post " +
    "from the briefing (pass the status URL from GROUNDING), get_post_replies " +
    "when they ask about comments/replies under a post, and read_url only " +
    "for a non-X article URL after get_post shows a linked_urls entry. " +
    "Call them when the user wants the latest, and summarize results " +
    "naturally (mention who posted by display name). If a tool " +
    "returns an error, tell the user briefly and continue." +
    (grounding
      ? " IMPORTANT: when the user asks about something specific mentioned in " +
        "the briefing (a person, claim, or event), first check the GROUNDING " +
        "section below for the exact source post — it's the real material the " +
        "briefing was built from. Prefer get_post on that URL (then read_url on " +
        "a linked article if they want more) over a broad search or pulling " +
        "someone's whole post history, which is less precise."
      : "") +
    " If the user says 'wrap up' or 'that's it', give a one-line closing." +
    "\n\n=== TODAY'S BRIEFING ===\n" + state.brief +
    grounding +
    history;

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
  if (state.continuing) {
    // Resuming a saved thread: don't re-read the brief. Nudge the host with
    // recent context already in systemInstruction.
    state.skipNextHostTranscript = false;
    state.briefShown = true; // transcript already rendered from saved events
    send({
      clientContent: {
        turns: [{
          role: "user",
          parts: [{ text: "I'm back on this same conversation. Pick up where we left off — don't re-read the whole brief. A short 'welcome back' is fine, then wait for my next question." }],
        }],
        turnComplete: true,
      },
    });
    state.continuing = false;
    return;
  }
  // Fresh thread: one DM-style brief message up front.
  renderBriefMessage();
  state.skipNextHostTranscript = true;
  state.introStartedAt = Date.now();
  send({
    clientContent: {
      turns: [{ role: "user", parts: [{ text: "Please start my morning briefing now." }] }],
      turnComplete: true,
    },
  });
}

function handleServerContent(sc) {
  if (sc.interrupted) {
    // Stop queued audio only. Do NOT close the Host bubble and do NOT clear
    // intro suppression — Gemini VAD often marks `interrupted` between the
    // host's own phrases (and speaker→mic echo). Closing here was splitting
    // one reply into many HOST cards.
    stopPlayback();
    setStatus("listening", "listening");
    setPlayMode("listening");
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
    const uttered = String(sc.inputTranscription.text || "");
    if (state.skipNextHostTranscript) {
      // Mic often hears the host speakers during the intro read. Ignore echo
      // until the user has had a few seconds and says something substantive.
      const ready = Date.now() - (state.introStartedAt || 0) > 4000;
      if (!ready || uttered.trim().length < 8) {
        // drop echo
      } else {
        state.skipNextHostTranscript = false;
        stopPlayback();
        flushHostTurn();
        appendUserLive(uttered);
        setStatus("listening", "listening");
        setPlayMode("listening");
      }
    } else {
      stopPlayback();
      flushHostTurn(); // close Host bubble before You — next host reply is a new turn
      appendUserLive(uttered);
      setStatus("listening", "listening");
      setPlayMode("listening");
    }
  }
  if (sc.outputTranscription && sc.outputTranscription.text) {
    appendHostLive(sc.outputTranscription.text);
    if (!state.paused) {
      setStatus("live", "live");
      setPlayMode("speaking");
    }
  }
  if (sc.turnComplete) {
    flushUserTurn();
    // Keep Host bubble open across phrase-level turnComplete.
    if (state.liveHostEl) state.hostGapPending = true;
    setPlayMode("listening");
  }
}

function addToolResultLine(name, args, result) {
  const { el, body } = makeMsg("tool", "Tool · " + name);

  const argsText = Object.values(args || {}).filter((v) => v !== undefined && v !== "").join(", ");
  if (argsText) {
    const argsSpan = document.createElement("span");
    argsSpan.className = "line__tool-args";
    argsSpan.textContent = argsText;
    body.appendChild(argsSpan);
  }

  const list = document.createElement("ul");
  list.className = "tool-results";

  if (result && result.error) {
    const li = document.createElement("li");
    li.className = "tool-results__error";
    li.textContent = result.error;
    list.appendChild(li);
  } else if (name === "get_post") {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = (result && result.url) || "#";
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    const who = (result && (result.name || result.author)) || "post";
    a.textContent = `${who}: ${((result && result.text) || "").slice(0, 140)}`;
    li.appendChild(a);
    list.appendChild(li);
    for (const link of (result && result.linked_urls) || []) {
      const lli = document.createElement("li");
      const la = document.createElement("a");
      la.href = link.url || "#";
      la.target = "_blank";
      la.rel = "noopener noreferrer";
      la.textContent = link.title || link.url || "linked article";
      lli.appendChild(la);
      if (link.description) {
        const preview = document.createElement("div");
        preview.className = "tool-results__preview";
        preview.textContent = link.description.slice(0, 220);
        lli.appendChild(preview);
      }
      list.appendChild(lli);
    }
  } else if (name === "read_url") {
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
  body.appendChild(list);
  appendMsg(el);
}

async function handleToolCall(toolCall) {
  // A tool call is proof the model has moved on to a new response — if any
  // audio from a prior turn is still playing, cut it now rather than let it
  // finish alongside a reaction to something newer (belt-and-braces alongside
  // the inputTranscription-triggered stop above).
  stopPlayback();
  // Flush any host text that finished before the tool call, then clear.
  flushHostTurn();
  state.hostBuf = "";
  state.liveHostEl = null;

  const calls = toolCall.functionCalls || [];
  const functionResponses = [];
  for (const call of calls) {
    let result;
    try {
      const r = await apiFetch("/tool", {
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
    clearConnectTimer();
    setPhase("live");
    kickOff();
    return;
  }
  if (msg.toolCall) { handleToolCall(msg.toolCall); return; }
  if (msg.serverContent) handleServerContent(msg.serverContent);
  if (msg.error) {
    console.error("Gemini error", msg.error);
    setStatus("error", "error");
    showError(msg.error.message || JSON.stringify(msg.error));
  }
}

// ---------- Mic capture ----------

async function requestMicAndAudio() {
  // MUST run inside the Start tap's user-gesture window. On iOS/Safari, if we
  // await a network fetch first, getUserMedia / AudioContext.resume() hang
  // forever with no prompt — which looks like "stuck on connecting".
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error("This browser can't access the microphone (needs HTTPS).");
  }
  state.micStream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
  });
  state.ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: INPUT_RATE });
  await state.ctx.resume();
}

function wireMicPipeline() {
  if (!state.ctx || !state.micStream) return;
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

function clearConnectTimer() {
  if (state.connectTimer) {
    clearTimeout(state.connectTimer);
    state.connectTimer = null;
  }
}

function failConnect(msg) {
  clearConnectTimer();
  console.error(msg);
  setPhase("error");
  showError(msg);
  // Tear down a half-open socket so Retry can start clean.
  if (state.ws) {
    try { state.ws.onclose = null; state.ws.close(); } catch (_) {}
    state.ws = null;
  }
}

// ---------- Lifecycle ----------

function newSessionId() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return (
    d.getUTCFullYear() +
    pad(d.getUTCMonth() + 1) +
    pad(d.getUTCDate()) +
    "T" +
    pad(d.getUTCHours()) +
    pad(d.getUTCMinutes()) +
    pad(d.getUTCSeconds()) +
    "Z"
  );
}

function scheduleSave() {
  if (state.saveTimer) clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(() => { persistThread(false); }, 800);
}

async function persistThread(keepalive) {
  // Mid-call autosave must NOT flush live bubbles — that was splitting Host
  // cards whenever anything logged. Only finalize turns on hang-up / unload.
  if (keepalive || state.phase === "hungup" || !state.ws) {
    flushHostTurn();
    flushUserTurn();
  }
  if (!state.sessionId) {
    if (state.sessionEvents.length === 0) return null;
    state.sessionId = newSessionId();
    state.startedAt = state.startedAt || new Date().toISOString();
  }
  const payload = {
    id: state.sessionId,
    started_at: state.startedAt,
    updated_at: new Date().toISOString(),
    brief: state.brief,
    brief_title: state.briefTitle,
    brief_items: state.briefItems,
    model: state.model,
    events: state.sessionEvents,
  };
  try {
    const r = await apiFetch("/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: !!keepalive,
    });
    const j = await r.json();
    if (j.id) state.sessionId = j.id;
    refreshSessionList(state.sessionId);
    setPhase(state.phase); // refresh synth button enablement
    return j;
  } catch (_) {
    return null;
  }
}

function renderSavedEvents(events) {
  els.captions.innerHTML = "";
  state.briefShown = false;
  // Prefer the structured brief bubble once, then non-intro turns.
  if (state.brief) renderBriefMessage();
  for (const ev of events || []) {
    if (ev.type === "host" && ev.intro) continue;
    if (ev.type === "host" && (ev.text || "").trim()) {
      const { el, body } = makeMsg("host", "Host");
      for (const para of splitIntoParas(ev.text)) {
        const p = document.createElement("p");
        appendTextWithInlinePosts(p, para);
        body.appendChild(p);
      }
      appendMsg(el);
    } else if (ev.type === "user" && (ev.text || "").trim()) {
      const { el, body } = makeMsg("you", "You");
      addPara(body, ev.text);
      appendMsg(el);
    } else if (ev.type === "tool_call") {
      addToolResultLine(ev.name, ev.args || {}, ev.result || {});
    }
  }
}

async function refreshSessionList(selectId) {
  try {
    const r = await apiFetch("/sessions");
    const j = await r.json();
    const sessions = j.sessions || [];
    const cur = selectId || state.sessionId || "";
    els.sessionSelect.innerHTML = "";
    const optNew = document.createElement("option");
    optNew.value = "";
    optNew.textContent = "New conversation";
    els.sessionSelect.appendChild(optNew);
    for (const s of sessions) {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = formatSessionLabel(s);
      els.sessionSelect.appendChild(opt);
    }
    els.sessionSelect.value = cur;
  } catch (_) { /* ignore */ }
}

async function refreshDraftList(selectId) {
  if (!els.draftSelect) return;
  try {
    const r = await apiFetch("/drafts");
    const j = await r.json();
    const drafts = j.drafts || [];
    const cur = selectId || state.draftId || "";
    els.draftSelect.innerHTML = "";
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = drafts.length ? "Drafts library" : "No drafts yet";
    els.draftSelect.appendChild(opt0);
    for (const d of drafts) {
      const opt = document.createElement("option");
      opt.value = d.id;
      const when = (d.generated_at || "").replace("T", " ").replace("Z", "").slice(0, 16);
      const pub = d.published ? " · published" : "";
      const prev = (d.preview || "").slice(0, 42);
      opt.textContent = `${when || d.id}${pub}${prev ? " — " + prev : ""}`;
      els.draftSelect.appendChild(opt);
    }
    if (cur) els.draftSelect.value = cur;
  } catch (_) { /* ignore */ }
}

async function loadDraftById(draftId) {
  if (!draftId) return;
  const r = await apiFetch(`/draft?id=${encodeURIComponent(draftId)}`);
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
  showDraft(j);
  refreshDraftList(j.id || draftId);
}

async function generateTodayBrief() {
  if (!els.generateBriefBtn) return;
  els.generateBriefBtn.disabled = true;
  els.generateBriefBtn.textContent = "Generating…";
  setBriefToast("Pulling new bookmarks…");
  try {
    const r = await apiFetch("/brief/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || j.error || `HTTP ${r.status}`);
    applyBriefPayload(j.brief || {});
    const n = j.new_bookmarks != null ? j.new_bookmarks : "?";
    setBriefToast(`Ready — ${n} new bookmark(s). Tap Start to listen.`);
    els.briefPanel.open = true;
  } catch (err) {
    setBriefToast(err.message || String(err), true);
  } finally {
    els.generateBriefBtn.textContent = "Generate today's brief";
    setPhase(state.phase);
  }
}

async function loadThread(sessionId) {
  if (!sessionId) {
    resetToNewThread();
    return;
  }
  const r = await apiFetch(`/session?id=${encodeURIComponent(sessionId)}`);
  if (!r.ok) throw new Error("Could not load that conversation");
  const data = await r.json();
  hangUpLiveOnly(); // ensure no live socket while browsing history
  state.sessionId = data.id || sessionId;
  state.startedAt = data.started_at || null;
  state.sessionEvents = data.events || [];
  state.brief = data.brief || state.brief;
  state.briefTitle = data.brief_title || "";
  state.briefItems = data.brief_items || state.briefItems || [];
  state.continuing = state.sessionEvents.length > 0;
  els.briefPanel.classList.add("is-hidden");
  els.draftPanel.classList.add("is-hidden");
  renderSavedEvents(state.sessionEvents);
  setPhase(state.sessionEvents.length ? "hungup" : "idle");
  refreshSessionList(state.sessionId);
}

function resetToNewThread() {
  hangUpLiveOnly();
  state.sessionId = null;
  state.sessionEvents = [];
  state.startedAt = null;
  state.continuing = false;
  state.briefShown = false;
  state.skipNextHostTranscript = false;
  state.hostBuf = "";
  state.userBuf = "";
  state.liveHostEl = null;
  state.liveUserEl = null;
  els.captions.innerHTML = '<p class="thread__hint">Your brief lands here like a DM — Hang up keeps the thread; Synthesize turns it into a post draft.</p>';
  els.draftPanel.classList.add("is-hidden");
  els.briefPanel.classList.remove("is-hidden");
  setPhase("idle");
  els.sessionSelect.value = "";
}

function hangUpLiveOnly() {
  // Tear down mic/ws without wiping the thread.
  clearConnectTimer();
  if (state.ws) {
    try { state.ws.onclose = null; state.ws.close(); } catch (_) {}
    state.ws = null;
  }
  stopPlayback();
  if (state.micNode) { try { state.micNode.disconnect(); } catch (_) {} state.micNode.onaudioprocess = null; state.micNode = null; }
  if (state.micSource) { try { state.micSource.disconnect(); } catch (_) {} state.micSource = null; }
  if (state.micStream) { state.micStream.getTracks().forEach((t) => t.stop()); state.micStream = null; }
  if (state.ctx) { try { state.ctx.close(); } catch (_) {} state.ctx = null; }
  state.paused = false;
  state.muted = false;
  els.muteBtn.textContent = "Mute mic";
  els.muteBtn.classList.remove("is-muted");
}

async function start() {
  const resuming = !!(state.sessionId && state.sessionEvents.length);
  state.continuing = resuming;
  setPhase("connecting");
  if (!resuming) {
    state.sessionEvents = [];
    state.sessionId = newSessionId();
    state.startedAt = new Date().toISOString();
    state.briefShown = false;
    els.captions.innerHTML = "";
  } else if (!state.startedAt) {
    state.startedAt = new Date().toISOString();
  }
  els.briefPanel.classList.add("is-hidden");
  els.draftPanel.classList.add("is-hidden");
  state.skipNextHostTranscript = false;
  state.hostBuf = "";
  state.userBuf = "";
  state.liveHostEl = null;
  state.liveUserEl = null;
  clearConnectTimer();

  try {
    els.playHint.textContent = "Allow microphone…";
    await requestMicAndAudio();

    els.playHint.textContent = "Getting session…";
    const [config, brief] = await Promise.all([
      apiFetch("/config").then(async (r) => {
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || j.error || `config HTTP ${r.status}`);
        return j;
      }),
      apiFetch("/brief").then((r) => r.json()),
    ]);

    if (!config.hasKey || !config.token) {
      const detail = config.error ? `: ${config.error}` : "";
      throw new Error(`Could not get a Gemini session token${detail}. Check GEMINI_API_KEY in .env.`);
    }

    state.model = config.model || "gemini-3.1-flash-live-preview";
    state.voice = config.voice || "Puck";
    // Keep brief from the loaded thread if present; otherwise take today's.
    if (!resuming || !state.brief) {
      applyBriefPayload(brief);
    } else {
      els.briefText.textContent = state.brief || "(no brief)";
      updateBriefBadge();
    }

    els.playHint.textContent = "Connecting to Gemini…";
    const url = `${config.wsBase}?access_token=${encodeURIComponent(config.token)}`;
    state.ws = new WebSocket(url);

    state.connectTimer = setTimeout(() => {
      if (state.phase === "connecting") {
        failConnect("Timed out waiting for Gemini (20s). Check network / API key, then tap Retry.");
      }
    }, 20000);

    state.ws.onopen = () => {
      wireMicPipeline();
      sendSetup();
    };
    state.ws.onmessage = (m) => { handleMessage(m.data); };
    state.ws.onerror = (e) => {
      console.error("WebSocket error", e);
      if (state.phase === "connecting") {
        failConnect("WebSocket failed. If you're on WiFi that blocks tunnels/Google, try cellular.");
      } else {
        setPhase("error");
      }
    };
    state.ws.onclose = () => {
      clearConnectTimer();
      if (state.phase === "connecting") {
        failConnect("Connection closed before the session started. Tap Retry.");
        return;
      }
      // Unexpected drop mid-call → keep the thread, mark hung up.
      if (state.phase === "live" || state.phase === "paused") {
        persistThread(true);
        hangUpLiveOnly();
        setPhase("hungup");
      }
      setPlayMode("idle");
    };
  } catch (err) {
    console.error(err);
    const name = err && err.name;
    let msg = err.message || String(err);
    if (name === "NotAllowedError" || /Permission|NotAllowed/i.test(msg)) {
      msg = "Microphone permission denied. Allow mic for this site, then tap Retry.";
    } else if (name === "NotFoundError") {
      msg = "No microphone found on this device.";
    }
    failConnect(msg);
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
    if (state.ctx) state.ctx.suspend();
    setPlayMode("idle");
    setPhase("paused");
  } else {
    if (state.ctx) state.ctx.resume();
    setPhase("live");
  }
}

function handlePlayTap() {
  if (state.phase === "connecting") return;
  if (state.phase === "idle" || state.phase === "error" || state.phase === "hungup") {
    start();
  } else {
    togglePause();
  }
}

async function hangUp() {
  if (state.phase !== "live" && state.phase !== "paused") return;
  await persistThread(true);
  hangUpLiveOnly();
  setPhase("hungup");
  els.playHint.textContent = "Thread saved — Continue Live, or Synthesize a post draft";
}

function formatDraft(draft) {
  if (!draft) return "";
  if (Array.isArray(draft.thread) && draft.thread.length) {
    return draft.thread.map((p) => String(p)).join("\n\n---\n\n");
  }
  return draft.text || "";
}

function parseDraftEditor(raw) {
  const text = (raw || "").trim();
  if (!text) return { text: "" };
  if (text.includes("\n---\n")) {
    const parts = text.split(/\n---\n/).map((p) => p.trim()).filter(Boolean);
    if (parts.length > 1) return { thread: parts };
  }
  return { text };
}

function showDraft(draft) {
  state.draftObj = draft || null;
  state.draftId = (draft && draft.id) || null;
  const text = formatDraft(draft);
  els.draftText.value = text || "";
  els.draftPanel.classList.remove("is-hidden");
  let meta = state.draftId ? `Draft ${state.draftId}` : "Draft";
  if (draft && draft.published_at) {
    meta += ` · published ${draft.published_at}`;
  } else {
    meta += " · edit, then Publish (confirm required — never auto-posts)";
  }
  els.draftMeta.textContent = meta;
  if (draft && Array.isArray(draft.urls) && draft.urls.length) {
    els.draftResult.classList.remove("is-hidden", "is-error");
    els.draftResult.innerHTML = "Live: " + draft.urls.map((u) => `<a href="${u}" target="_blank" rel="noopener">${u}</a>`).join(" · ");
  } else {
    els.draftResult.classList.add("is-hidden");
    els.draftResult.textContent = "";
  }
  els.draftPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function synthesize() {
  await persistThread(false);
  if (!state.sessionId) {
    showError("Nothing to synthesize yet — talk a bit first.");
    return;
  }
  els.synthBtn.disabled = true;
  els.synthBtn.textContent = "Synthesizing…";
  try {
    const r = await apiFetch("/synthesize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.sessionId }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || j.error || `HTTP ${r.status}`);
    showDraft(j.draft);
    refreshDraftList(j.draft && j.draft.id);
  } catch (err) {
    showError("Synthesize failed: " + (err.message || err));
  } finally {
    els.synthBtn.textContent = "Synthesize";
    setPhase(state.phase);
  }
}

async function publishDraft() {
  const parsed = parseDraftEditor(els.draftText.value);
  if (!parsed.text && !(parsed.thread && parsed.thread.length)) {
    showError("Draft is empty — synthesize or type something first.");
    return;
  }
  const ok = window.confirm(
    "Publish this draft to your authenticated X account?\n\n"
    + "This will call xurl POST /2/tweets (needs tweet.write). "
    + "Nothing is posted unless you confirm."
  );
  if (!ok) return;

  els.publishBtn.disabled = true;
  els.publishBtn.textContent = "Publishing…";
  els.draftResult.classList.add("is-hidden");
  try {
    const body = {
      confirm: true,
      draft_id: state.draftId || "latest",
    };
    if (parsed.thread) body.thread = parsed.thread;
    else body.text = parsed.text;
    const r = await apiFetch("/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
    state.draftId = j.draft_id || state.draftId;
    els.draftResult.classList.remove("is-hidden", "is-error");
    const links = (j.urls || []).map((u) => `<a href="${u}" target="_blank" rel="noopener">${u}</a>`).join(" · ");
    els.draftResult.innerHTML = "Published: " + (links || (j.tweet_ids || []).join(", "));
    els.draftMeta.textContent = `Draft ${state.draftId || ""} · published ${j.published_at || ""}`;
  } catch (err) {
    els.draftResult.classList.remove("is-hidden");
    els.draftResult.classList.add("is-error");
    els.draftResult.textContent = "Publish failed: " + (err.message || err);
  } finally {
    els.publishBtn.disabled = false;
    els.publishBtn.textContent = "Publish to X";
  }
}

els.playBtn.addEventListener("click", handlePlayTap);
els.muteBtn.addEventListener("click", toggleMute);
els.hangupBtn.addEventListener("click", hangUp);
els.synthBtn.addEventListener("click", synthesize);
els.publishBtn.addEventListener("click", publishDraft);
if (els.generateBriefBtn) {
  els.generateBriefBtn.addEventListener("click", () => {
    generateTodayBrief().catch((err) => setBriefToast(err.message || String(err), true));
  });
}
els.newThreadBtn.addEventListener("click", () => {
  hangUpLiveOnly();
  resetToNewThread();
});
els.sessionSelect.addEventListener("change", () => {
  const id = els.sessionSelect.value;
  loadThread(id).catch((err) => showError(err.message || String(err)));
});
if (els.draftSelect) {
  els.draftSelect.addEventListener("change", () => {
    const id = els.draftSelect.value;
    if (!id) return;
    loadDraftById(id).catch((err) => showError(err.message || String(err)));
  });
}
els.copyDraftBtn.addEventListener("click", async () => {
  const text = els.draftText.value || "";
  try {
    await navigator.clipboard.writeText(text);
    els.copyDraftBtn.textContent = "Copied";
    setTimeout(() => { els.copyDraftBtn.textContent = "Copy"; }, 1200);
  } catch (_) {
    els.copyDraftBtn.textContent = "Copy failed";
  }
});

setPhase("idle");
refreshSessionList();
refreshDraftList();

// Preload the brief so the panel shows content before starting.
apiFetch("/brief").then((r) => r.json()).then((b) => {
  applyBriefPayload(b);
}).catch(() => {});
