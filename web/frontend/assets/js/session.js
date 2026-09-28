import {
  onAuthStateChanged,
  signOut,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";
import { auth } from "./firebase-config.js";

const userEmailEl = document.getElementById("site-user-email");
const loginLink = document.getElementById("site-login-link");
const logoutButton = document.getElementById("site-logout-button");
const LOGIN_PAGE = "login.html";

function showLoggedOutState() {
  userEmailEl?.classList.add("hidden");
  logoutButton?.classList.add("hidden");
  loginLink?.classList.remove("hidden");
  window.location.href = LOGIN_PAGE;
}

function showLoggedInState(user) {
  if (userEmailEl) {
    userEmailEl.textContent = user.displayName || user.email || "Logged in";
    userEmailEl.classList.remove("hidden");
  }

  loginLink?.classList.add("hidden");
  logoutButton?.classList.remove("hidden");
}

onAuthStateChanged(auth, (user) => {
  if (user) {
    showLoggedInState(user);
    return;
  }

  showLoggedOutState();
});

logoutButton?.addEventListener("click", async () => {
  await signOut(auth);
  window.location.href = "login.html";
});
