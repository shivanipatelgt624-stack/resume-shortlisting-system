@echo off
echo Starting Resume Shortlisting System...
echo =======================================
echo.

cd /d "C:\Users\Shivani Patel G T\Documents\resume_shortlisting_system"
call .venv\Scripts\activate.bat

echo Virtual Environment Activated!
echo Server is starting up...
echo.

start http://127.0.0.1:5000

:: Using the absolute path to flask just to be 100% sure
.venv\Scripts\flask.exe run --port=5000

pause
