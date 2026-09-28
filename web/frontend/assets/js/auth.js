import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  updateProfile,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";
import { auth } from "./firebase-config.js";

const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const loginEmailInput = document.getElementById("login-email");
const loginPasswordInput = document.getElementById("login-password");
const registerUsernameInput = document.getElementById("register-username");
const registerEmailInput = document.getElementById("register-email");
const registerPasswordInput = document.getElementById("register-password");
const loginButton = document.getElementById("login-button");
const registerButton = document.getElementById("register-button");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const statusEl = document.getElementById("auth-status");
const registerStatusEl = document.getElementById("register-status");
const loginEmailError = document.getElementById("login-email-error");
const registerUsernameError = document.getElementById("register-username-error");
const registerEmailError = document.getElementById("register-email-error");
const loginPasswordError = document.getElementById("login-password-error");
const registerPasswordError = document.getElementById("register-password-error");
const authNavButton = document.getElementById("auth-nav-button");
const showRegisterButton = document.getElementById("show-register-button");
const showLoginButton = document.getElementById("show-login-button");
const popup = document.querySelector(".auth-popup");
const policyCheckbox = document.getElementById("policy");
const forgotPasswordLink = document.querySelector(".forgot-pass");

function setStatus(message) {
  if (statusEl) {
    statusEl.textContent = message;
  }
}

function setRegisterStatus(message) {
  if (registerStatusEl) {
    registerStatusEl.textContent = message;
  }
}

function setFieldError(element, message) {
  if (element) {
    element.textContent = message;
  }
}

function friendlyAuthError(error) {
  const code = error?.code || "";

  if (code.includes("invalid-api-key") || code.includes("app/no-options")) {
    return "Firebase config is not set yet. Paste your Firebase config first.";
  }
  if (code.includes("auth/invalid-email")) {
    return "Please enter a valid email address.";
  }
  if (code.includes("auth/invalid-credential") || code.includes("auth/wrong-password")) {
    return "Email or password is incorrect.";
  }
  if (code.includes("auth/user-not-found")) {
    return "No account found with this email. Please sign up first.";
  }
  if (code.includes("auth/email-already-in-use")) {
    return "This email is already registered. Please log in instead.";
  }
  if (code.includes("auth/weak-password")) {
    return "Password must be at least 6 characters.";
  }

  return error?.message || "Something went wrong. Please try again.";
}

function isPasswordAuthError(error) {
  const code = error?.code || "";
  return code.includes("auth/invalid-credential") ||
    code.includes("auth/wrong-password") ||
    code.includes("auth/weak-password");
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function getRegisterPasswordError(password) {
  if (!password) {
    return "Please create a password.";
  }
  if (password.length < 6) {
    return "Password must be at least 6 characters.";
  }
  if (!/[A-Z]/.test(password)) {
    return "Password must include at least one capital letter.";
  }
  return "";
}

function getUsernameError(username) {
  if (!username) {
    return "Please enter your username.";
  }
  if (username.length < 3) {
    return "Username must be at least 3 characters.";
  }
  if (username.length > 20) {
    return "Username cannot be more than 20 characters.";
  }
  return "";
}

function validateRegisterPassword() {
  const password = registerPasswordInput?.value || "";
  const message = getRegisterPasswordError(password);
  setFieldError(registerPasswordError, message);
  return !message;
}

function showRegisterPanel() {
  popup?.classList.add("show-register");
  if (authNavButton) {
    authNavButton.textContent = "Login";
  }
  setStatus("");
  setFieldError(loginEmailError, "");
  setFieldError(loginPasswordError, "");
}

function showLoginPanel() {
  popup?.classList.remove("show-register");
  if (authNavButton) {
    authNavButton.textContent = "Sign Up";
  }
  setRegisterStatus("");
  setFieldError(registerUsernameError, "");
  setFieldError(registerEmailError, "");
  setFieldError(registerPasswordError, "");
}

onAuthStateChanged(auth, (user) => {
  if (user) {
    setStatus(`Already logged in as ${user.displayName || user.email}. You can continue, or sign up with another account.`);
  }
});

async function loginUser() {
  try {
    setStatus("Logging in...");
    setFieldError(loginEmailError, "");
    setFieldError(loginPasswordError, "");
    const email = (loginEmailInput?.value || emailInput?.value || "").trim();
    const password = loginPasswordInput?.value || passwordInput?.value || "";

    if (!email) {
      setStatus("");
      setFieldError(loginEmailError, "Please enter your email.");
      return;
    }

    if (!password) {
      setStatus("");
      setFieldError(loginPasswordError, "Please enter your password.");
      return;
    }

    if (!isValidEmail(email)) {
      setStatus("");
      setFieldError(loginEmailError, "Please enter a valid email format, for example name@example.com.");
      return;
    }

    await signInWithEmailAndPassword(auth, email, password);
    window.location.href = "index.html";
  } catch (error) {
    const message = friendlyAuthError(error);
    if (isPasswordAuthError(error)) {
      setStatus("");
      setFieldError(loginPasswordError, message);
      return;
    }
    setStatus(message);
  }
}

async function registerUser() {
  try {
    setFieldError(registerEmailError, "");
    setFieldError(registerPasswordError, "");
    setFieldError(registerUsernameError, "");

    setRegisterStatus("Creating account...");
    const username = (registerUsernameInput?.value || "").trim();
    const email = (registerEmailInput?.value || emailInput?.value || "").trim();
    const password = registerPasswordInput?.value || passwordInput?.value || "";

    const usernameError = getUsernameError(username);
    if (usernameError) {
      setRegisterStatus("");
      setFieldError(registerUsernameError, usernameError);
      return;
    }

    if (!email) {
      setRegisterStatus("");
      setFieldError(registerEmailError, "Please enter your email.");
      return;
    }

    if (!password) {
      setRegisterStatus("");
      setFieldError(registerPasswordError, "Please create a password.");
      return;
    }

    if (!isValidEmail(email)) {
      setRegisterStatus("");
      setFieldError(registerEmailError, "Please enter a valid email format, for example name@example.com.");
      return;
    }

    const passwordError = getRegisterPasswordError(password);
    if (passwordError) {
      setRegisterStatus("");
      setFieldError(registerPasswordError, passwordError);
      return;
    }

    if (policyCheckbox && !policyCheckbox.checked) {
      setRegisterStatus("Please agree Terms & Condition before creating the account.");
      return;
    }

    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    await updateProfile(userCredential.user, {
      displayName: username,
    });
    window.location.href = "index.html";
  } catch (error) {
    const message = friendlyAuthError(error);
    if (isPasswordAuthError(error)) {
      setRegisterStatus("");
      setFieldError(registerPasswordError, message);
      return;
    }
    setRegisterStatus(message);
  }
}

async function resetPassword() {
  const email = (loginEmailInput?.value || emailInput?.value || "").trim();
  setFieldError(loginEmailError, "");

  if (!email) {
    setFieldError(loginEmailError, "Enter your email first, then click Forgot password.");
    return;
  }

  if (!isValidEmail(email)) {
    setFieldError(loginEmailError, "Please enter a valid email address.");
    return;
  }

  try {
    await sendPasswordResetEmail(auth, email);
    setStatus("Password reset email sent. Check your inbox and spam folder.");
  } catch (error) {
    const code = error?.code || "";
    if (code.includes("auth/user-not-found")) {
      setStatus("No account was found with this email address.");
      return;
    }
    setStatus(friendlyAuthError(error));
  }
}

loginButton.addEventListener("click", loginUser);
registerButton.addEventListener("click", registerUser);
forgotPasswordLink?.addEventListener("click", (event) => {
  event.preventDefault();
  resetPassword();
});

loginForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  loginUser();
});

registerForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  registerUser();
});

showRegisterButton?.addEventListener("click", showRegisterPanel);

showLoginButton?.addEventListener("click", showLoginPanel);

authNavButton?.addEventListener("click", () => {
  if (popup?.classList.contains("show-register")) {
    showLoginPanel();
    return;
  }

  showRegisterPanel();
});

loginEmailInput?.addEventListener("input", () => {
  setFieldError(loginEmailError, "");
});

registerEmailInput?.addEventListener("input", () => {
  setFieldError(registerEmailError, "");
});

registerUsernameInput?.addEventListener("input", () => {
  setFieldError(registerUsernameError, "");
});

loginPasswordInput?.addEventListener("input", () => {
  setFieldError(loginPasswordError, "");
});

registerPasswordInput?.addEventListener("input", () => {
  validateRegisterPassword();
});

registerPasswordInput?.addEventListener("blur", () => {
  validateRegisterPassword();
});
