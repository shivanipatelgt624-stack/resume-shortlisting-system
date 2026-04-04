import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, GoogleAuthProvider, signInWithPopup } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js";

// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
    apiKey: "AIzaSyBdKAU54xnYicWuiCtXtyBcoRCX46VBh14",
    authDomain: "resume-shortlisting-syst-99aa4.firebaseapp.com",
    projectId: "resume-shortlisting-syst-99aa4",
    storageBucket: "resume-shortlisting-syst-99aa4.firebasestorage.app",
    messagingSenderId: "190123003145",
    appId: "1:190123003145:web:1975cd57956fd54067d7d8",
    measurementId: "G-X8ZS15G6QC"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

export { auth, signInWithEmailAndPassword, createUserWithEmailAndPassword, googleProvider, signInWithPopup };
