@echo off
setlocal

echo ============================================
echo  Starting BillerQ AI Assistant
echo ============================================

:: Start the AI backend from the ai-agent folder
echo [1/2] Starting AI backend on port 8080...
start "BillerQ AI Backend" cmd /k "cd /d %~dp0ai-agent && python -m uvicorn app:app --reload --host 127.0.0.1 --port 8080"

:: Start the React frontend
echo [2/2] Starting BillerQ frontend on port 3030...
if exist "%~dp0build\index.html" (
    start "BillerQ Frontend" cmd /k "cd /d %~dp0 && python serve_frontend.py"
) else (
    echo WARNING: build/index.html not found. Frontend will not start.
)

:: Give the servers time to boot, then open the browser
echo Waiting for servers to boot...
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:3030/signin"

echo.
echo ============================================
echo  Servers started!
echo  Frontend : http://127.0.0.1:3030
echo  Backend  : http://127.0.0.1:8080
echo  Widget   : http://127.0.0.1:8080/widget
echo ============================================

endlocal
exit /b 0
