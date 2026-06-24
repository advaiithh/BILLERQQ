@echo off
setlocal

:: Start backend from ai-agent
pushd %~dp0ai-agent
if exist "%~dp0.venv\Scripts\Activate.bat" (
    call "%~dp0.venv\Scripts\Activate.bat"
) else (
    echo WARNING: virtualenv activation script not found at %~dp0.venv\Scripts\Activate.bat
)
start "BillerQ Backend" cmd /k "python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000"
popd

:: Start frontend from build folder with SPA support
cd /d %~dp0
if exist "%~dp0build\index.html" (
    start "BillerQ Frontend" cmd /k "python serve_frontend.py"
) else (
    echo WARNING: build/index.html not found. Frontend server will not start.
)

:: Give the servers a moment, then open the frontend login page
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:3000/signin"

endlocal
exit /b 0
