import {
  getIdToken,
  onAuthStateChanged,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";
import {
  addDoc,
  collection,
  getDocs,
  orderBy,
  query,
  serverTimestamp,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js";
import {
  getDownloadURL,
  ref,
  uploadBytes,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-storage.js";
import { auth, db, storage } from "./firebase-config.js";
import {
  preparePianoRoll,
  renderPianoRoll,
  resetPianoRoll,
  startPianoRollAnimation,
  stopPianoRollAnimation,
  updatePianoRollPlayhead,
} from "./piano-roll.js";

const chatWindow = document.getElementById("chat-window");
const form = document.getElementById("music-form");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const generateButton = document.getElementById("generate-button");
const statusEl = document.getElementById("status");
const sidebarStatusEl = document.getElementById("sidebar-status");
const downloadLink = document.getElementById("download-link");
const trackTitle = document.getElementById("track-title");
const trackDescription = document.getElementById("track-description");
const resultMeta = document.getElementById("result-meta");
const playerWidget = document.getElementById("player-widget");
const playerToggle = document.getElementById("player-toggle");
const playerCaption = document.getElementById("player-caption");
const audioPlayer = document.getElementById("audio-player");
const libraryList = document.getElementById("library-list");
const libraryRefreshButton = document.getElementById("library-refresh");
const chatHistoryList = document.getElementById("chat-history-list");
const chatHistoryRefreshButton = document.getElementById("chat-history-refresh");
const siteNavbar = document.querySelector(".site-navbar");
const conversationHistory = [];
const userConversationMemory = [];
const conversationPreferences = {
  emotion: "",
  instruments: [],
  style: "",
  drums: "",
  atmosphere: [],
};
const knownEmotionKeywords = [
  "happy",
  "sad",
  "energetic",
  "relaxed",
  "angry",
  "melancholic",
  "romantic",
  "anxious",
  "hopeful",
  "lonely",
];
const knownStyleKeywords = ["jazz", "rock", "pop", "lofi", "cinematic", "orchestral", "ambient", "classical"];
const knownAtmosphereKeywords = [
  "soft",
  "gentle",
  "dark",
  "bright",
  "dramatic",
  "emotional",
  "calm",
  "peaceful",
  "intense",
  "uplifting",
  "warm",
  "sad",
  "melancholic",
  "romantic",
  "anxious",
  "hopeful",
  "lonely",
];
const knownInstrumentKeywords = [
  "english horn",
  "double bass",
  "grand piano",
  "electric piano",
  "acoustic guitar",
  "electric guitar",
  "pan flute",
  "alto sax",
  "tenor sax",
  "baritone sax",
  "soprano sax",
  "french horn",
  "piano",
  "violin",
  "viola",
  "cello",
  "contrabass",
  "harp",
  "timpani",
  "choir",
  "oboe",
  "bassoon",
  "clarinet",
  "piccolo",
  "flute",
  "recorder",
  "sax",
  "trumpet",
  "trombone",
  "tuba",
  "horn",
  "brass",
  "guitar",
  "bass",
  "strings",
  "string",
  "pad",
  "vocal",
  "lead",
  "synth",
  "organ",
  "drums",
  "drum",
  "xylophone",
];

let lastUserMessage = "";
let lastScrollY = window.scrollY;
let currentUser = null;

let midiPlayerState = {
  midiUrl: "",
  isReady: false,
  isPlaying: false,
  synths: [],
  drumSynth: null,
  hatSynth: null,
  parts: [],
};

const chipGroups = {
  emotion: document.querySelectorAll("#emotion-chips .chip"),
};

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getSelectedChips(group) {
  return [...chipGroups[group]]
    .filter((chip) => chip.classList.contains("selected"))
    .map((chip) => chip.textContent.trim());
}

function timestampLabel() {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function appendMessage(text, sender) {
  const safeText = escapeHtml(text);
  const bubble = document.createElement("article");
  bubble.className = `message ${sender}`;
  bubble.innerHTML = `
    <p>${safeText}</p>
    <span class="time-stamp">${timestampLabel()}</span>
  `;
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  conversationHistory.push({
    role: sender === "bot" ? "assistant" : "user",
    content: text,
  });
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function formatLibraryTime(value) {
  if (!value) {
    return "Unknown time";
  }

  if (typeof value.toDate === "function") {
    return value.toDate().toLocaleString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  const normalized = String(value).replace(
    /^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/,
    "$1-$2-$3T$4:$5:$6"
  );
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildPromptSummaryFromLibrary(item) {
  const summary = [];
  if (item.emotion) {
    summary.push(`Mood: ${item.emotion}`);
  }
  if (item.arrangement?.lead || item.arrangement?.harmony || item.arrangement?.bass) {
    summary.push(
      [
        item.arrangement?.lead ? `Lead ${item.arrangement.lead}` : "",
        item.arrangement?.harmony ? `Harmony ${item.arrangement.harmony}` : "",
        item.arrangement?.bass ? `Bass ${item.arrangement.bass}` : "",
      ].filter(Boolean).join(", ")
    );
  }
  return summary.join(" | ") || "Previously generated track";
}

function cleanPromptText(value = "") {
  return String(value)
    .replaceAll(" | ", "\n")
    .replace(/^Notes:\s*/gim, "")
    .trim();
}

function promptToInputText(value = "") {
  const text = String(value).trim();
  const notesMatch = text.match(/(?:^|\|\s*)Notes:\s*([^|]+)/i);
  if (notesMatch?.[1]) {
    return notesMatch[1].trim();
  }
  return text
    .replace(/\s*\|\s*/g, ". ")
    .replace(/Mood:\s*/gi, "")
    .replace(/Instruments:\s*/gi, "with ")
    .replace(/Style:\s*/gi, "")
    .replace(/Atmosphere:\s*/gi, "")
    .trim();
}

function regenerateFromLibraryItem(item) {
  const promptText = promptToInputText(item.prompt || buildPromptSummaryFromLibrary(item));
  input.value = promptText;
  lastUserMessage = promptText;

  updateConversationPreferences({
    userText: promptText,
    selectedEmotion: item.emotion ? [String(item.emotion)] : [],
  });

  setStatus("Loaded the previous prompt. Review it, then click Generate Music.");
  document.querySelector(".assistant-panel")?.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
  input.focus();
}

function regenerateFromChatItem(item) {
  const promptText = promptToInputText(item.promptSummary || item.userMessage || "");
  input.value = promptText;
  lastUserMessage = promptText;

  updateConversationPreferences({
    userText: promptText,
    selectedEmotion: item.emotion ? [String(item.emotion)] : [],
  });

  setStatus("Loaded the previous conversation prompt. Review it, then click Generate Music.");
  document.querySelector(".assistant-panel")?.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
  input.focus();
}

function absoluteUrl(path) {
  if (!path) {
    return "";
  }
  return new URL(path, window.location.origin).toString();
}

async function uploadOutputFile(sourceUrl, fileName, contentType) {
  if (!currentUser || !sourceUrl || !fileName) {
    return "";
  }

  const response = await fetch(absoluteUrl(sourceUrl));
  if (!response.ok) {
    throw new Error(`Could not read generated file for upload: ${fileName}`);
  }

  const blob = await response.blob();
  const outputRef = ref(storage, `users/${currentUser.uid}/outputs/${fileName}`);
  await uploadBytes(outputRef, blob, {
    contentType,
  });
  return getDownloadURL(outputRef);
}

async function uploadGeneratedFiles(data) {
  if (!currentUser) {
    return data;
  }

  const uploaded = { ...data };

  if (data.download_url && data.midi_file) {
    uploaded.download_url = await uploadOutputFile(
      data.download_url,
      data.midi_file,
      "audio/midi"
    );
    uploaded.storage_midi_path = `users/${currentUser.uid}/outputs/${data.midi_file}`;
  }

  if (data.audio_url && data.audio_file) {
    uploaded.audio_url = await uploadOutputFile(
      data.audio_url,
      data.audio_file,
      "audio/wav"
    );
    uploaded.storage_audio_path = `users/${currentUser.uid}/outputs/${data.audio_file}`;
  }

  return uploaded;
}

// save the history data generated by user
async function saveGenerationHistory(data, promptSummary) {
  if (!currentUser) {
    return;
  }

  const historyRef = collection(db, "users", currentUser.uid, "generations");
  await addDoc(historyRef, {
    prompt: promptSummary,
    emotion: data.emotion || "neutral",
    arrangement: data.arrangement || {},
    midi_file: data.midi_file || "",
    audio_file: data.audio_file || "",
    download_url: absoluteUrl(data.download_url),
    audio_url: absoluteUrl(data.audio_url),
    storage_midi_path: data.storage_midi_path || "",
    storage_audio_path: data.storage_audio_path || "",
    token_count: data.token_count || 0,
    selection_metrics: data.selection_metrics || {},
    created_at: data.created_at || "",
    createdAt: serverTimestamp(),
    user_email: currentUser.email || "",
    user_name: currentUser.displayName || "",
  });
}

async function saveChatHistory({ userMessage, botReply, promptSummary, emotionResult, conversationState }) {
  if (!currentUser) {
    return;
  }

  const chatRef = collection(db, "users", currentUser.uid, "chatHistory");
  await addDoc(chatRef, {
    userMessage: userMessage || "",
    botReply: botReply || "",
    promptSummary: promptSummary || "",
    emotion: emotionResult?.emotion || conversationState?.emotion || "neutral",
    conversationState: conversationState || {},
    createdAt: serverTimestamp(),
    user_email: currentUser.email || "",
    user_name: currentUser.displayName || "",
  });
}

async function readJsonResponse(response) {
  const rawText = await response.text();

  if (!rawText.trim()) {
    throw new Error("The server returned an empty response. Restart the Python server and try again.");
  }

  try {
    return JSON.parse(rawText);
  } catch (error) {
    throw new Error(`The server returned an invalid response: ${rawText.slice(0, 160)}`);
  }
}

async function buildAuthHeaders() {
  const headers = {
    "Content-Type": "application/json",
  };

  if (currentUser) {
    headers.Authorization = `Bearer ${await getIdToken(currentUser)}`;
  }

  return headers;
}

function buildPrompt(userText = "") {
  const emotion = getSelectedChips("emotion");
  const currentState = buildStructuredConversationState(userText);
  const effectiveEmotion = emotion[0] || currentState.emotion || conversationPreferences.emotion;
  const effectiveInstruments = currentState.instruments;

  const segments = [
    effectiveEmotion ? `Mood: ${effectiveEmotion}` : "",
    effectiveInstruments.length ? `Instruments: ${effectiveInstruments.join(", ")}` : "",
    currentState.style ? `Style: ${currentState.style}` : "",
    currentState.drums ? `Drums: ${currentState.drums}` : "",
    currentState.atmosphere.length ? `Atmosphere: ${currentState.atmosphere.join(", ")}` : "",
    userText ? `Notes: ${userText}` : "",
  ].filter(Boolean);

  return segments.join(" | ");
}

function uniquePreserveOrder(values) {
  const seen = new Set();
  const result = [];

  values.forEach((value) => {
    const normalized = String(value).trim().toLowerCase();
    if (!normalized || seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    result.push(String(value).trim());
  });

  return result;
}

function extractEmotionFromText(text = "") {
  const normalized = String(text).toLowerCase();

  return knownEmotionKeywords.find((keyword) => {
    const pattern = new RegExp(`\\b${keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
    return pattern.test(normalized);
  }) || "";
}

function extractInstrumentsFromText(text = "") {
  const normalized = String(text).toLowerCase();

  return knownInstrumentKeywords
    .slice()
    .sort((left, right) => right.length - left.length)
    .filter((keyword) => {
      const pattern = new RegExp(`\\b${keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
      return pattern.test(normalized);
    });
}

function extractStyleFromText(text = "") {
  const normalized = String(text).toLowerCase();

  return knownStyleKeywords.find((keyword) => {
    const pattern = new RegExp(`\\b${keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
    return pattern.test(normalized);
  }) || "";
}

function extractDrumPreference(text = "") {
  const normalized = String(text).toLowerCase();

  if (/\b(no drum|no drums|without drum|without drums)\b/i.test(normalized)) {
    return "no";
  }
  if (/\b(drum|drums|beat|percussion|rhythm)\b/i.test(normalized)) {
    return "yes";
  }
  return "";
}

function extractAtmosphereFromText(text = "") {
  const normalized = String(text).toLowerCase();

  return knownAtmosphereKeywords.filter((keyword) => {
    const pattern = new RegExp(`\\b${keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
    return pattern.test(normalized);
  });
}

function buildStructuredConversationState(currentInput = "") {
  const detectedEmotion = extractEmotionFromText(currentInput);
  const currentInstruments = extractInstrumentsFromText(currentInput);
  const style = extractStyleFromText(currentInput);
  const drums = extractDrumPreference(currentInput);
  const atmosphere = extractAtmosphereFromText(currentInput);

  return {
    emotion: conversationPreferences.emotion || detectedEmotion,
    instruments: uniquePreserveOrder([
      ...conversationPreferences.instruments,
      ...currentInstruments,
    ]),
    style: conversationPreferences.style || style,
    drums: conversationPreferences.drums || drums,
    atmosphere: uniquePreserveOrder([
      ...conversationPreferences.atmosphere,
      ...atmosphere,
    ]),
  };
}

function updateConversationPreferences({ userText = "", selectedEmotion = [], emotionResult = "" } = {}) {
  const derivedEmotion = selectedEmotion[0] || extractEmotionFromText(userText) || emotionResult;
  if (derivedEmotion && derivedEmotion !== "neutral") {
    conversationPreferences.emotion = derivedEmotion;
  }

  const derivedInstruments = extractInstrumentsFromText(userText);
  if (derivedInstruments.length) {
    conversationPreferences.instruments = uniquePreserveOrder([
      ...conversationPreferences.instruments,
      ...derivedInstruments,
    ]);
  }

  const derivedStyle = extractStyleFromText(userText);
  if (derivedStyle) {
    conversationPreferences.style = derivedStyle;
  }

  const drumPreference = extractDrumPreference(userText);
  if (drumPreference) {
    conversationPreferences.drums = drumPreference;
  }

  const atmosphere = extractAtmosphereFromText(userText);
  if (atmosphere.length) {
    conversationPreferences.atmosphere = uniquePreserveOrder([
      ...conversationPreferences.atmosphere,
      ...atmosphere,
    ]);
  }
}

function buildConversationMemory(currentInput = "") {
  const memory = [...userConversationMemory];
  const trimmedCurrent = currentInput.trim();

  if (trimmedCurrent) {
    memory.push(trimmedCurrent);
  }

  return memory
    .map((item) => String(item).trim())
    .filter(Boolean)
    .slice(-6)
    .join("\n");
}

function disposeMidiPlayback() {
  Tone.Transport.stop();
  Tone.Transport.cancel();

  midiPlayerState.parts.forEach((part) => part.dispose());
  midiPlayerState.parts = [];

  midiPlayerState.synths.forEach((synth) => synth.dispose());
  if (midiPlayerState.drumSynth) {
    midiPlayerState.drumSynth.dispose();
  }
  if (midiPlayerState.hatSynth) {
    midiPlayerState.hatSynth.dispose();
  }

  midiPlayerState = {
    midiUrl: "",
    isReady: false,
    isPlaying: false,
    synths: [],
    drumSynth: null,
    hatSynth: null,
    parts: [],
  };

  playerToggle.textContent = "Play Preview";
  stopPianoRollAnimation();
  updatePianoRollPlayhead(0);
}

function resetAudioPlayback() {
  audioPlayer.pause();
  audioPlayer.removeAttribute("src");
  audioPlayer.load();
  audioPlayer.classList.add("hidden");
}

async function prepareMidiPlayback(midiUrl) {
  disposeMidiPlayback();

  if (!window.Tone || !window.Midi) {
    throw new Error("The browser MIDI player could not be loaded.");
  }

  const response = await fetch(midiUrl);
  if (!response.ok) {
    throw new Error("Could not load the generated MIDI for playback.");
  }

  const arrayBuffer = await response.arrayBuffer();
  const midi = new Midi(arrayBuffer);
  renderPianoRoll(midi, midiUrl);

  const drumSynth = new Tone.MembraneSynth({
    pitchDecay: 0.03,
    octaves: 6,
    envelope: {
      attack: 0.001,
      decay: 0.25,
      sustain: 0.01,
      release: 0.15,
    },
  }).toDestination();
  const hatSynth = new Tone.MetalSynth({
    frequency: 250,
    envelope: {
      attack: 0.001,
      decay: 0.08,
      release: 0.03,
    },
    harmonicity: 5.1,
    modulationIndex: 32,
    resonance: 3000,
    octaves: 1.5,
  }).toDestination();

  const parts = [];
  const synths = [];
  Tone.Transport.bpm.value = midi.header.tempos?.[0]?.bpm || 120;

  function createTrackSynth(track) {
    const instrumentName = String(track.instrument?.name || "").toLowerCase();
    const familyName = String(track.instrument?.family || "").toLowerCase();
    const trackName = String(track.name || "").toLowerCase();
    const descriptor = `${instrumentName} ${familyName} ${trackName}`;

    if (descriptor.match(/xylophone|marimba|vibraphone|glockenspiel|bells/)) {
      return new Tone.PolySynth(Tone.FMSynth, {
        harmonicity: 3,
        modulationIndex: 8,
        envelope: { attack: 0.001, decay: 0.18, sustain: 0.15, release: 0.4 },
        modulationEnvelope: { attack: 0.001, decay: 0.12, sustain: 0.05, release: 0.2 },
      }).toDestination();
    }

    if (descriptor.match(/bass/)) {
      return new Tone.PolySynth(Tone.MonoSynth, {
        oscillator: { type: "square" },
        filter: { Q: 2, type: "lowpass", rolloff: -24 },
        envelope: { attack: 0.01, decay: 0.25, sustain: 0.45, release: 0.7 },
        filterEnvelope: { attack: 0.01, decay: 0.12, sustain: 0.25, release: 0.4, baseFrequency: 90, octaves: 2 },
      }).toDestination();
    }

    if (descriptor.match(/string|choir|pad/)) {
      return new Tone.PolySynth(Tone.AMSynth, {
        harmonicity: 1.5,
        envelope: { attack: 0.08, decay: 0.2, sustain: 0.65, release: 1.2 },
      }).toDestination();
    }

    if (descriptor.match(/guitar|harp/)) {
      return new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: "triangle" },
        envelope: { attack: 0.004, decay: 0.18, sustain: 0.24, release: 0.55 },
      }).toDestination();
    }

    if (descriptor.match(/brass|trumpet|horn|sax/)) {
      return new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: "sawtooth" },
        envelope: { attack: 0.02, decay: 0.15, sustain: 0.4, release: 0.5 },
      }).toDestination();
    }

    if (descriptor.match(/organ/)) {
      return new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: "square4" },
        envelope: { attack: 0.01, decay: 0.1, sustain: 0.8, release: 0.2 },
      }).toDestination();
    }

    return new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: "triangle" },
      envelope: {
        attack: 0.01,
        decay: 0.2,
        sustain: 0.35,
        release: 0.8,
      },
    }).toDestination();
  }

  midi.tracks.forEach((track) => {
    if (!track.notes.length) {
      return;
    }

    const isDrumTrack = Boolean(track.instrument?.percussion) ||
      /drum|percussion/i.test(track.name || "");
    const synth = isDrumTrack ? null : createTrackSynth(track);
    if (synth) {
      synths.push(synth);
    }

    const part = new Tone.Part((time, note) => {
      if (isDrumTrack) {
        if (note.midi <= 38) {
          drumSynth.triggerAttackRelease("C1", "16n", time, 0.9);
        } else if (note.midi <= 42) {
          drumSynth.triggerAttackRelease("G1", "16n", time, 0.7);
        } else {
          hatSynth.triggerAttackRelease("16n", time, 0.35);
        }
        return;
      }

      synth.triggerAttackRelease(
        note.name,
        Math.max(note.duration, 0.08),
        time,
        Math.max(0.25, Math.min(note.velocity ?? 0.8, 1))
      );
    }, track.notes.map((note) => [note.time, note]));

    part.start(0);
    parts.push(part);
  });

  midiPlayerState = {
    midiUrl,
    isReady: true,
    isPlaying: false,
    synths,
    drumSynth,
    hatSynth,
    parts,
  };

  if (!parts.length) {
    throw new Error("The generated MIDI has no playable note data.");
  }
}

async function startMidiPlayback() {
  if (!midiPlayerState.isReady) {
    return;
  }

  await Tone.start();
  Tone.Transport.stop();
  Tone.Transport.position = 0;
  Tone.Transport.start();
  midiPlayerState.isPlaying = true;
  playerToggle.textContent = "Pause Preview";
  playerCaption.textContent = "Playing the generated MIDI directly in the browser.";
  startPianoRollAnimation("midi");
}

function stopMidiPlayback() {
  Tone.Transport.stop();
  Tone.Transport.position = 0;
  midiPlayerState.isPlaying = false;
  playerToggle.textContent = "Play Preview";
  playerCaption.textContent = "The generated MIDI is ready for playback.";
  stopPianoRollAnimation();
  updatePianoRollPlayhead(0);
}

function renderResult(data, promptSummary) {
  trackTitle.textContent = "Generated Track Ready";
  trackDescription.textContent = promptSummary;
  const arrangement = data.arrangement || {};
  const detectedEmotion = String(data.emotion || "neutral");
  const barCount = data.bars ?? data.selection_metrics?.bars ?? "-";
  const modelName = data.model_name || data.requested_model || "-";
  const fallbackReason = data.fallback_reason || "";
  const createdAt = data.created_at || "-";
  const instruments = Array.isArray(data.instruments) ? data.instruments : [];
  const isMidiGpt = String(modelName).toLowerCase().includes("midi-gpt");
  const arrangementSummary = [
    instruments.length ? `Instruments: ${instruments.join(", ")}` : "",
    arrangement.lead ? `Lead: ${arrangement.lead}` : "",
    arrangement.harmony ? `Harmony: ${arrangement.harmony}` : "",
    arrangement.bass ? `Bass: ${arrangement.bass}` : "",
    arrangement.add_drums === "yes" ? "Drums: enabled" : "",
  ].filter(Boolean).join(" | ");
  const instrumentDetails = isMidiGpt ? `
    <div>
      <span>Instruments</span>
      <strong>${escapeHtml(instruments.length ? instruments.join(", ") : "-")}</strong>
    </div>
    <div>
      <span>MIDI-GPT Bars</span>
      <strong>${escapeHtml(String(data.midigpt_generated_bars || data.selection_metrics?.midigpt_generated_bars || "-"))}</strong>
    </div>
  ` : `
    <div>
      <span>Lead</span>
      <strong>${escapeHtml(String(arrangement.lead || "-"))}</strong>
    </div>
    <div>
      <span>Harmony</span>
      <strong>${escapeHtml(String(arrangement.harmony || "-"))}</strong>
    </div>
    <div>
      <span>Bass</span>
      <strong>${escapeHtml(String(arrangement.bass || "-"))}</strong>
    </div>
  `;

  sidebarStatusEl.textContent = arrangementSummary
    ? `${data.midi_file} created successfully. Emotion: ${detectedEmotion}. ${arrangementSummary}`
    : `${data.midi_file} created successfully. Emotion: ${detectedEmotion}.`;
  resultMeta.innerHTML = `
    <div>
      <span>Bars</span>
      <strong>${escapeHtml(String(barCount))}</strong>
    </div>
    <div>
      <span>Model</span>
      <strong>${escapeHtml(String(modelName))}</strong>
    </div>
    ${fallbackReason ? `
    <div>
      <span>Fallback</span>
      <strong>${escapeHtml(String(fallbackReason))}</strong>
    </div>` : ""}
    <div>
      <span>Duration</span>
      <strong>${escapeHtml(String(Number(data.selection_metrics?.output_seconds || 0).toFixed(2)))}s</strong>
    </div>
    <div>
      <span>Created</span>
      <strong>${escapeHtml(String(createdAt))}</strong>
    </div>
    <div>
      <span>Emotion</span>
      <strong>${escapeHtml(detectedEmotion)}</strong>
    </div>
    ${instrumentDetails}
  `;

  downloadLink.href = encodeURI(data.download_url);
  downloadLink.setAttribute("download", data.midi_file || "generated_music.mid");
  downloadLink.classList.remove("hidden");

  if (data.audio_url) {
    audioPlayer.src = encodeURI(data.audio_url);
    audioPlayer.classList.remove("hidden");
    playerToggle.classList.add("hidden");
    playerCaption.textContent = "WAV preview is ready. Press play to listen directly in the browser.";
  } else {
    audioPlayer.classList.add("hidden");
    playerToggle.classList.remove("hidden");
    playerCaption.textContent = "WAV preview is unavailable, so the browser is using MIDI preview.";
  }

  playerWidget.classList.remove("hidden");
}

async function openLibraryItem(item) {
  renderResult(item, buildPromptSummaryFromLibrary(item));
  playerToggle.textContent = "Play Preview";
  playerToggle.classList.remove("hidden");
  playerToggle.disabled = true;
  disposeMidiPlayback();
  resetAudioPlayback();
  resetPianoRoll();

  if (item.download_url) {
    await preparePianoRoll(encodeURI(item.download_url)).catch((error) => {
      playerCaption.textContent = error.message || "Piano roll preview could not be loaded.";
    });
  }

  if (item.audio_url) {
    audioPlayer.src = encodeURI(item.audio_url);
    audioPlayer.classList.remove("hidden");
    playerToggle.classList.add("hidden");
    playerCaption.textContent = "WAV preview is ready. Press play to listen directly in the browser.";
    await audioPlayer.play().catch(() => {});
    startPianoRollAnimation("audio");
  } else if (item.download_url) {
    await prepareMidiPlayback(encodeURI(item.download_url));
    playerToggle.disabled = false;
  }

  setStatus("Loaded a previous output from the library.");
}

function renderLibrary(items) {
  if (!libraryList) {
    return;
  }

  if (!items.length) {
    libraryList.innerHTML = `<p class="library-empty">No saved generations yet. Generate a track and it will appear here.</p>`;
    return;
  }

  libraryList.innerHTML = items.map((item, index) => {
    const arrangement = item.arrangement || {};
    const promptText = cleanPromptText(item.prompt || buildPromptSummaryFromLibrary(item));
    const emotion = item.emotion || "neutral";
    const createdTime = item.createdAt || item.created_at;
    const audioUrl = item.audio_url || "";
    const midiUrl = item.download_url || "";
    const summary = [
      arrangement.lead ? `Lead ${arrangement.lead}` : "",
      arrangement.harmony ? `Harmony ${arrangement.harmony}` : "",
      arrangement.bass ? `Bass ${arrangement.bass}` : "",
      arrangement.add_drums ? `Drums ${arrangement.add_drums}` : "",
    ].filter(Boolean).join(" · ");

    return `
      <article class="library-item">
        <div class="library-item-main">
          <div class="library-title-row">
            <h3>${escapeHtml(item.midi_file || `Generated Track ${index + 1}`)}</h3>
            <span class="library-emotion">${escapeHtml(String(emotion))}</span>
          </div>
          <p class="library-prompt">${escapeHtml(promptText || "Generated output")}</p>
          <div class="library-tags">
            ${summary ? `<span>${escapeHtml(summary)}</span>` : ""}
            <span>${escapeHtml(formatLibraryTime(createdTime))}</span>
            ${item.token_count ? `<span>${escapeHtml(String(item.token_count))} tokens</span>` : ""}
          </div>
        </div>
        <div class="library-actions">
          <button class="library-button" type="button" data-library-index="${index}">${audioUrl ? "Play" : "Open"}</button>
          <button class="library-link" type="button" data-regenerate-index="${index}">Regenerate</button>
          ${midiUrl ? `<a class="library-link" href="${encodeURI(midiUrl)}" download="${escapeHtml(item.midi_file || "generated_music.mid")}">MIDI</a>` : ""}
          ${audioUrl ? `<a class="library-link" href="${encodeURI(audioUrl)}" download="${escapeHtml(item.audio_file || "generated_music.wav")}">WAV</a>` : ""}
        </div>
      </article>
    `;
  }).join("");

  [...libraryList.querySelectorAll("[data-library-index]")].forEach((button) => {
    button.addEventListener("click", async () => {
      const index = Number(button.getAttribute("data-library-index"));
      const item = window.generatedLibraryItems?.[index];
      if (!item) {
        return;
      }
      try {
        await openLibraryItem(item);
      } catch (error) {
        setStatus(error.message || "Could not load the selected library item.", true);
      }
    });
  });

  [...libraryList.querySelectorAll("[data-regenerate-index]")].forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.getAttribute("data-regenerate-index"));
      const item = window.generatedLibraryItems?.[index];
      if (!item) {
        return;
      }
      regenerateFromLibraryItem(item);
    });
  });
}

async function loadLibrary() {
  if (!libraryList) {
    return;
  }

  if (currentUser) {
    try {
      const historyRef = collection(db, "users", currentUser.uid, "generations");
      const historyQuery = query(historyRef, orderBy("createdAt", "desc"));
      const snapshot = await getDocs(historyQuery);

      window.generatedLibraryItems = snapshot.docs.map((doc) => ({
        id: doc.id,
        ...doc.data(),
      }));
      renderLibrary(window.generatedLibraryItems);
      return;
    } catch (error) {
      libraryList.innerHTML = `<p class="library-empty">${escapeHtml(error.message || "Could not load your saved history.")}</p>`;
      return;
    }
  }

  try {
    const response = await fetch("/api/library");
    const data = await readJsonResponse(response);

    if (!response.ok) {
      throw new Error(data.error || "Could not load the output library.");
    }

    window.generatedLibraryItems = data.items || [];
    renderLibrary(window.generatedLibraryItems);
  } catch (error) {
    libraryList.innerHTML = `<p class="library-empty">${escapeHtml(error.message || "Could not load the output library.")}</p>`;
  }
}

function renderChatHistory(items) {
  if (!chatHistoryList) {
    return;
  }

  if (!items.length) {
    chatHistoryList.innerHTML = `<p class="library-empty">No saved conversations yet. Chat with the assistant and the conversation will appear here.</p>`;
    return;
  }

  chatHistoryList.innerHTML = items.map((item, index) => `
    <article class="library-item chat-history-item">
      <div class="library-item-main">
        <div class="library-title-row">
          <h3>${escapeHtml(item.userMessage || `Conversation ${index + 1}`)}</h3>
          <span class="library-emotion">${escapeHtml(String(item.emotion || "neutral"))}</span>
        </div>
        <p class="library-prompt">${escapeHtml(item.botReply || "No assistant reply saved.")}</p>
        <div class="library-tags">
          ${item.promptSummary ? `<span>${escapeHtml(cleanPromptText(item.promptSummary))}</span>` : ""}
          <span>${escapeHtml(formatLibraryTime(item.createdAt))}</span>
        </div>
      </div>
      <div class="library-actions">
        <button class="library-link" type="button" data-chat-regenerate-index="${index}">Regenerate</button>
      </div>
    </article>
  `).join("");

  [...chatHistoryList.querySelectorAll("[data-chat-regenerate-index]")].forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.getAttribute("data-chat-regenerate-index"));
      const item = window.savedChatHistoryItems?.[index];
      if (!item) {
        return;
      }
      regenerateFromChatItem(item);
    });
  });
}

async function loadChatHistory() {
  if (!chatHistoryList || !currentUser) {
    renderChatHistory([]);
    return;
  }

  try {
    const chatRef = collection(db, "users", currentUser.uid, "chatHistory");
    const chatQuery = query(chatRef, orderBy("createdAt", "desc"));
    const snapshot = await getDocs(chatQuery);
    window.savedChatHistoryItems = snapshot.docs.map((doc) => ({
      id: doc.id,
      ...doc.data(),
    }));
    renderChatHistory(window.savedChatHistoryItems);
  } catch (error) {
    chatHistoryList.innerHTML = `<p class="library-empty">${escapeHtml(error.message || "Could not load saved conversations.")}</p>`;
  }
}

Object.values(chipGroups).forEach((group) => {
  group.forEach((chip) => {
    chip.addEventListener("click", () => {
      group.forEach((item) => item.classList.remove("selected"));
      chip.classList.add("selected");
      if (group === chipGroups.emotion) {
        conversationPreferences.emotion = chip.textContent.trim().toLowerCase();
      }
    });
  });
});

const pendingRegeneratePrompt = localStorage.getItem("textMuseRegeneratePrompt");
if (pendingRegeneratePrompt) {
  input.value = pendingRegeneratePrompt;
  lastUserMessage = pendingRegeneratePrompt;
  updateConversationPreferences({
    userText: pendingRegeneratePrompt,
  });
  localStorage.removeItem("textMuseRegeneratePrompt");
  setStatus("Loaded a previous prompt. Review it, then click Generate Music.");
}

conversationHistory.push({
  role: "assistant",
  content:
    "Hi! I am your FYP music assistant. You can leave emotion unselected, or choose an emotion such as happy, sad, relaxed, angry, energetic, melancholic, romantic, anxious, hopeful, or lonely, then tell me the style and instruments you want.",
});

libraryRefreshButton?.addEventListener("click", async () => {
  await loadLibrary();
});

chatHistoryRefreshButton?.addEventListener("click", async () => {
  await loadChatHistory();
});

playerToggle.addEventListener("click", async () => {
  if (!midiPlayerState.isReady) {
    return;
  }

  try {
    if (midiPlayerState.isPlaying) {
      stopMidiPlayback();
      return;
    }

    playerToggle.disabled = true;
    await startMidiPlayback();
  } catch (error) {
    setStatus(error.message || "Could not start MIDI playback.", true);
    playerCaption.textContent = "Playback could not be started for this MIDI file.";
  } finally {
    playerToggle.disabled = false;
  }
});

audioPlayer?.addEventListener("play", () => {
  startPianoRollAnimation("audio");
});

audioPlayer?.addEventListener("pause", () => {
  stopPianoRollAnimation();
});

audioPlayer?.addEventListener("ended", () => {
  stopPianoRollAnimation();
  updatePianoRollPlayhead(0);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const userText = input.value.trim();
  const promptSummary = buildPrompt(userText);

  if (!promptSummary) {
    setStatus("Add a short prompt or select a few preferences first.", true);
    return;
  }

  const chatMessage = userText || promptSummary;

  lastUserMessage = chatMessage;
  userConversationMemory.push(chatMessage);
  updateConversationPreferences({
    userText: chatMessage,
    selectedEmotion: getSelectedChips("emotion"),
  });
  appendMessage(promptSummary, "user");
  sendButton.disabled = true;
  setStatus("Thinking... the chatbot is preparing a response.");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: chatMessage,
        prompt_summary: promptSummary,
        messages: conversationHistory.slice(0, -1),
        conversation_memory: buildConversationMemory(),
        conversation_state: buildStructuredConversationState(chatMessage),
        emotion: getSelectedChips("emotion"),
        emotion_label: getSelectedChips("emotion")[0]?.toLowerCase() || "",
      }),
    });

    const data = await readJsonResponse(response);

    if (!response.ok) {
      throw new Error(data.error || "Chat request failed.");
    }

    appendMessage(data.reply, "bot");
    await saveChatHistory({
      userMessage: chatMessage,
      botReply: data.reply,
      promptSummary,
      emotionResult: data.emotion_result,
      conversationState: buildStructuredConversationState(chatMessage),
    });
    await loadChatHistory();
    updateConversationPreferences({
      userText: chatMessage,
      selectedEmotion: getSelectedChips("emotion"),
      emotionResult: String(data.emotion_result?.emotion || ""),
    });
    setStatus(`Chatbot ready. Model: ${data.model || "OpenAI"}`);
    input.value = "";
  } catch (error) {
    conversationHistory.pop();
    chatWindow.lastElementChild?.remove();
    setStatus(error.message || "Something went wrong while contacting the chatbot.", true);
  } finally {
    sendButton.disabled = false;
  }
});

generateButton.addEventListener("click", async () => {
  const currentInput = input.value.trim();
  const conversationMemory = buildConversationMemory(currentInput);
  const conversationState = buildStructuredConversationState(currentInput);
  const promptSummary = buildPrompt(
    currentInput || "Generate a polished multi-instrument composition."
  );

  generateButton.disabled = true;
  sendButton.disabled = true;
  playerWidget.classList.add("hidden");
  playerCaption.textContent = "The generated MIDI is ready for playback.";
  playerToggle.textContent = "Play Preview";
  playerToggle.classList.remove("hidden");
  playerToggle.disabled = true;
  disposeMidiPlayback();
  resetAudioPlayback();
  resetPianoRoll();
  setStatus("Generating music... the model is building a new MIDI arrangement.");

  try {
    if (window.Tone) {
      await Tone.start();
    }

    const response = await fetch("/api/generate", {
      method: "POST",
      headers: await buildAuthHeaders(),
      body: JSON.stringify({
        prompt: promptSummary,
        message: lastUserMessage || currentInput,
        conversation_memory: conversationMemory,
        conversation_state: conversationState,
        messages: conversationHistory.slice(),
        emotion: getSelectedChips("emotion"),
        style: conversationState.style ? [conversationState.style] : [],
        instruments: conversationState.instruments,
        model: "midi-gpt",
        emotion_label: getSelectedChips("emotion")[0]?.toLowerCase() || "",
        use_emotion_override: true,
      }),
    });

    const data = await readJsonResponse(response);

    if (!response.ok) {
      throw new Error(data.error || "Music generation failed.");
    }

    appendMessage(
      "Your MIDI output is ready. You can review the result details and download the generated file.",
      "bot"
    );
    renderResult(data, promptSummary);
    await preparePianoRoll(encodeURI(data.download_url));
    setStatus("Uploading generated files to Firebase Storage...");
    const storedData = await uploadGeneratedFiles(data);
    await saveGenerationHistory(storedData, promptSummary);
    await loadLibrary();
    if (data.audio_url) {
      playerToggle.disabled = true;
      await audioPlayer.play().catch(() => {});
      startPianoRollAnimation("audio");
    } else {
      await prepareMidiPlayback(encodeURI(data.download_url));
      playerToggle.disabled = false;
      await startMidiPlayback();
    }
    setStatus("Music generated successfully. Your MIDI file is ready to download.");
  } catch (error) {
    setStatus(error.message || "Something went wrong while generating music.", true);
    playerWidget.classList.add("hidden");
  } finally {
    generateButton.disabled = false;
    sendButton.disabled = false;
  }
});

onAuthStateChanged(auth, (user) => {
  currentUser = user;
  loadLibrary();
  loadChatHistory();
});

window.addEventListener("scroll", () => {
  if (!siteNavbar) {
    return;
  }

  const currentScrollY = window.scrollY;
  const isScrollingDown = currentScrollY > lastScrollY;

  if (isScrollingDown && currentScrollY > 90) {
    siteNavbar.classList.add("nav-hidden");
  } else {
    siteNavbar.classList.remove("nav-hidden");
  }

  lastScrollY = currentScrollY;
});
