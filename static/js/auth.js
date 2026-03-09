import { auth, signInWithEmailAndPassword, createUserWithEmailAndPassword } from './firebase-config.js';

document.addEventListener('DOMContentLoaded', () => {

    // Login Form Handler
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Logging in...';

            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            try {
                // 1. Authenticate with Firebase
                const userCredential = await signInWithEmailAndPassword(auth, email, password);
                const user = userCredential.user;

                // 2. Get ID Token
                const idToken = await user.getIdToken();

                // 3. Send token to our Flask backend to establish session
                const response = await fetch('/api/auth/sessionLogin', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ idToken })
                });

                const data = await response.json();

                if (response.ok) {
                    window.location.href = data.redirect || '/';
                } else {
                    alert(data.error || 'Failed to login to server');
                    auth.signOut(); // Revert Firebase auth if server fails
                }
            } catch (error) {
                console.error("Login error:", error);

                // Specifically check for wrong email or password
                if (error.code === 'auth/invalid-credential' ||
                    error.code === 'auth/wrong-password' ||
                    error.code === 'auth/user-not-found') {
                    alert("password or emaild id is wrong");
                } else {
                    alert("Login failed: " + error.message);
                }
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Log In';
            }
        });
    }

    // Register Form Handler
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = registerForm.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Signing up...';

            const fullname = document.getElementById('fullname').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const role = document.getElementById('role').value;

            try {
                // 1. Create user in Firebase
                const userCredential = await createUserWithEmailAndPassword(auth, email, password);
                const user = userCredential.user;

                // 2. Send metadata to our Flask backend
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        uid: user.uid,
                        email: user.email,
                        fullname: fullname,
                        role: role
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    window.location.href = data.redirect || '/';
                } else {
                    alert(data.error || 'Registration failed on server');
                    auth.currentUser.delete(); // Rollback Firebase user if backend fails
                }
            } catch (error) {
                console.error("Registration error:", error);
                alert("Registration failed: " + error.message);
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sign Up';
            }
        });
    }
});
