import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";
import {
  collection,
  deleteDoc,
  doc,
  getDocs,
  orderBy,
  query,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js";
import { auth, db } from "./firebase-config.js";

const historyList = document.getElementById("history-list");
const historyRefresh = document.getElementById("history-refresh");
const conversationList = document.getElementById("conversation-list");
const conversationRefresh = document.getElementById("conversation-refresh");

let currentUser = null;
let savedGenerationItems = [];
let savedConversationItems = [];

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatTime(value) {
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
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
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

function saveRegeneratePrompt(prompt) {
  localStorage.setItem("textMuseRegeneratePrompt", promptToInputText(prompt));
  window.location.href = "index.html";
}

function renderGenerations(items) {
  if (!historyList) {
    return;
  }

  if (!items.length) {
    historyList.innerHTML = `<p class="library-empty">No saved generations yet. Generate a track and it will appear here.</p>`;
    return;
  }

  historyList.innerHTML = items.map((item, index) => {
    const arrangement = item.arrangement || {};
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
            <span class="library-emotion">${escapeHtml(item.emotion || "neutral")}</span>
          </div>
          <p class="library-prompt">${escapeHtml(cleanPromptText(item.prompt || "Generated output"))}</p>
          <div class="library-tags">
            ${summary ? `<span>${escapeHtml(summary)}</span>` : ""}
            <span>${escapeHtml(formatTime(item.createdAt || item.created_at))}</span>
            ${item.token_count ? `<span>${escapeHtml(item.token_count)} tokens</span>` : ""}
          </div>
        </div>
        <div class="library-actions">
          ${item.audio_url ? `<a class="library-button" href="${encodeURI(item.audio_url)}">Play</a>` : ""}
          ${item.download_url ? `<a class="library-link" href="${encodeURI(item.download_url)}" download="${escapeHtml(item.midi_file || "generated_music.mid")}">MIDI</a>` : ""}
          ${item.audio_url ? `<a class="library-link" href="${encodeURI(item.audio_url)}" download="${escapeHtml(item.audio_file || "generated_music.wav")}">WAV</a>` : ""}
          <button class="library-link" type="button" data-generation-regenerate-index="${index}">Regenerate</button>
          <button class="library-danger" type="button" data-generation-delete-index="${index}">Delete Track</button>
        </div>
      </article>
    `;
  }).join("");

  [...historyList.querySelectorAll("[data-generation-regenerate-index]")].forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.getAttribute("data-generation-regenerate-index"));
      const item = savedGenerationItems[index];
      if (item) {
        saveRegeneratePrompt(item.prompt || "");
      }
    });
  });

  [...historyList.querySelectorAll("[data-generation-delete-index]")].forEach((button) => {
    button.addEventListener("click", async () => {
      const index = Number(button.getAttribute("data-generation-delete-index"));
      const item = savedGenerationItems[index];
      if (!item || !window.confirm("Delete this generated track from your history?")) {
        return;
      }

      await deleteDoc(doc(db, "users", currentUser.uid, "generations", item.id));
      await loadGenerations();
    });
  });
}

function renderConversations(items) {
  if (!conversationList) {
    return;
  }

  if (!items.length) {
    conversationList.innerHTML = `<p class="library-empty">No saved conversations yet. Chat with the assistant and the conversation will appear here.</p>`;
    return;
  }

  conversationList.innerHTML = items.map((item, index) => `
    <article class="library-item">
      <div class="library-item-main">
        <div class="library-title-row">
          <h3>${escapeHtml(item.userMessage || `Conversation ${index + 1}`)}</h3>
          <span class="library-emotion">${escapeHtml(item.emotion || "neutral")}</span>
        </div>
        <p class="library-prompt">${escapeHtml(item.botReply || "No assistant reply saved.")}</p>
        <div class="library-tags">
          ${item.promptSummary ? `<span>${escapeHtml(cleanPromptText(item.promptSummary))}</span>` : ""}
          <span>${escapeHtml(formatTime(item.createdAt))}</span>
        </div>
      </div>
      <div class="library-actions">
        <button class="library-link" type="button" data-conversation-regenerate-index="${index}">Regenerate</button>
        <button class="library-danger" type="button" data-conversation-delete-index="${index}">Delete Chat</button>
      </div>
    </article>
  `).join("");

  [...conversationList.querySelectorAll("[data-conversation-regenerate-index]")].forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.getAttribute("data-conversation-regenerate-index"));
      const item = savedConversationItems[index];
      if (item) {
        saveRegeneratePrompt(item.promptSummary || item.userMessage || "");
      }
    });
  });

  [...conversationList.querySelectorAll("[data-conversation-delete-index]")].forEach((button) => {
    button.addEventListener("click", async () => {
      const index = Number(button.getAttribute("data-conversation-delete-index"));
      const item = savedConversationItems[index];
      if (!item || !window.confirm("Delete this saved conversation?")) {
        return;
      }

      await deleteDoc(doc(db, "users", currentUser.uid, "chatHistory", item.id));
      await loadConversations();
    });
  });
}

async function loadGenerations() {
  if (!historyList || !currentUser) {
    return;
  }

  try {
    const historyRef = collection(db, "users", currentUser.uid, "generations");
    const historyQuery = query(historyRef, orderBy("createdAt", "desc"));
    const snapshot = await getDocs(historyQuery);
    savedGenerationItems = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
    renderGenerations(savedGenerationItems);
  } catch (error) {
    historyList.innerHTML = `<p class="library-empty">${escapeHtml(error.message || "Could not load saved generations.")}</p>`;
  }
}

async function loadConversations() {
  if (!conversationList || !currentUser) {
    return;
  }

  try {
    const chatRef = collection(db, "users", currentUser.uid, "chatHistory");
    const chatQuery = query(chatRef, orderBy("createdAt", "desc"));
    const snapshot = await getDocs(chatQuery);
    savedConversationItems = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
    renderConversations(savedConversationItems);
  } catch (error) {
    conversationList.innerHTML = `<p class="library-empty">${escapeHtml(error.message || "Could not load saved conversations.")}</p>`;
  }
}

onAuthStateChanged(auth, (user) => {
  currentUser = user;
  loadGenerations();
  loadConversations();
});

historyRefresh?.addEventListener("click", loadGenerations);
conversationRefresh?.addEventListener("click", loadConversations);
