@echo off
TITLE Aider AI Agent - Architect Mode
COLOR 0A

:: --- CONFIGURATION ---
:: Replace the path below with your actual project folder
set PROJECT_PATH=C:\hk\generator
set MODEL=ollama/deepseek-r1:7b

:: --- RAM OPTIMIZATIONS ---
:: Keeps the model in RAM for 24 hours so it doesn't reload every prompt
set OLLAMA_KEEP_ALIVE=24h

echo ===================================================
echo   LAUNCHING AI AGENT (DeepSeek 1.5B)
echo   Project: %PROJECT_PATH%
echo   Mode:    Architect (Think-then-Code)
echo ===================================================

:: Navigate to project
cd /d "%PROJECT_PATH%"

:: Check if the directory exists
if %errorlevel% neq 0 (
    echo [ERROR] Could not find folder: %PROJECT_PATH%
    pause
    exit /b
)

:: Run Aider
aider --model %MODEL% --architect

echo ===================================================
echo   Session Closed.
echo ===================================================
pause