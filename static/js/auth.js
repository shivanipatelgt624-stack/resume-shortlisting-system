import { auth, signInWithEmailAndPassword, createUserWithEmailAndPassword, googleProvider, signInWithPopup } from './firebase-config.js';

document.addEventListener('DOMContentLoaded', () => {

    // Helper: Finalize session with Flask backend after any Firebase login
    async function finalizeSession(user) {
        const idToken = await user.getIdToken();
        const response = await fetch('/api/auth/sessionLogin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idToken })
        });
        const data = await response.json();
        if (response.ok) {
            window.location.href = data.redirect || '/';
        } else {
            alert(data.error || 'Failed to login to server');
            auth.signOut();
        }
    }

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
                const userCredential = await signInWithEmailAndPassword(auth, email, password);
                await finalizeSession(userCredential.user);
            } catch (error) {
                console.error("Login error:", error);
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

        // Google Login Handler
        const googleLoginBtn = document.getElementById('google-login');
        if (googleLoginBtn) {
            googleLoginBtn.addEventListener('click', async () => {
                try {
                    const result = await signInWithPopup(auth, googleProvider);
                    await finalizeSession(result.user);
                } catch (error) {
                    console.error("Google Login error:", error);
                    alert("Google login failed: " + error.message);
                }
            });
        }
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
                const userCredential = await createUserWithEmailAndPassword(auth, email, password);
                const user = userCredential.user;

                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
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
                    auth.currentUser.delete();
                }
            } catch (error) {
                console.error("Registration error:", error);
                alert("Registration failed: " + error.message);
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sign Up';
            }
        });

        // Google Register Handler
        const googleRegisterBtn = document.getElementById('google-register');
        if (googleRegisterBtn) {
            googleRegisterBtn.addEventListener('click', async () => {
                const role = document.getElementById('role').value;
                if (!role) {
                    alert("Please select your role first!");
                    return;
                }

                try {
                    const result = await signInWithPopup(auth, googleProvider);
                    const user = result.user;

                    const response = await fetch('/api/auth/register', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            uid: user.uid,
                            email: user.email,
                            fullname: user.displayName || "Google User",
                            role: role,
                            profile_pic: user.photoURL
                        })
                    });

                    const data = await response.json();
                    if (response.ok) {
                        window.location.href = data.redirect || '/';
                    } else if (response.status === 409) {
                        // User already exists, try logging them in
                        await finalizeSession(user);
                    } else {
                        alert(data.error || 'Registration failed on server');
                    }
                } catch (error) {
                    console.error("Google Register error:", error);
                    alert("Google registration failed: " + error.message);
                }
            });
        }
    }
});
