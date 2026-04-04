@echo off
:: Resume Shortlisting System - Auto Start Server
cd /d "C:\Users\Shivani Patel G T\Documents\resume_shortlisting_system"

:: Kill any existing instance
taskkill /F /IM flask.exe /T >nul 2>&1

:: Start Flask server in background (hidden window)
start "" /B "C:\Users\Shivani Patel G T\Documents\resume_shortlisting_system\.venv\Scripts\flask.exe" run --port=5000

:: Wait 3 seconds then open browser
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5000
