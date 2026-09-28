import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js";
import { getStorage } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-storage.js";

const firebaseConfig = {
  apiKey: "AIzaSyDM4hadSgOJh7wP3mVsrtF3q78ldN5UXCc",
  authDomain: "fyp-project-db-c5ca9.firebaseapp.com",
  projectId: "fyp-project-db-c5ca9",
  storageBucket: "fyp-project-db-c5ca9.firebasestorage.app",
  messagingSenderId: "54613103691",
  appId: "1:54613103691:web:b722c9c8ce976f0855a9ce",
  measurementId: "G-P28612LF6L"
};

export const firebaseApp = initializeApp(firebaseConfig);
export const auth = getAuth(firebaseApp);
export const db = getFirestore(firebaseApp);
export const storage = getStorage(firebaseApp);
