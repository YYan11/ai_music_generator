import {
  onAuthStateChanged,
  signOut,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";
import {
  collection,
  getDocs,
  orderBy,
  query,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js";
import { auth, db } from "./firebase-config.js";

const historyList = document.getElementById("history-list");
const logoutButton = document.getElementById("logout-button");

function renderHistory(items) {
  if (!items.length) {
    historyList.innerHTML = `<p class="muted">No generation history yet.</p>`;
    return;
  }

  historyList.innerHTML = items.map((item) => `
    <article class="history-item">
      <h3>${item.emotion || "Generated Music"}</h3>
      <p>${item.prompt || ""}</p>
      <div class="button-row">
        ${item.audioUrl ? `<a href="${item.audioUrl}" download>Download WAV</a>` : ""}
        ${item.midiUrl ? `<a href="${item.midiUrl}" download>Download MIDI</a>` : ""}
      </div>
    </article>
  `).join("");
}

onAuthStateChanged(auth, async (user) => {
  if (!user) {
    window.location.href = "login.html";
    return;
  }

  const historyRef = collection(db, "users", user.uid, "generations");
  const historyQuery = query(historyRef, orderBy("createdAt", "desc"));
  const snapshot = await getDocs(historyQuery);
  const items = snapshot.docs.map((doc) => doc.data());
  renderHistory(items);
});

logoutButton.addEventListener("click", async () => {
  await signOut(auth);
  window.location.href = "login.html";
});
