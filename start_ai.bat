@echo off
TITLE Aider AI Agent - RAM Optimized
COLOR 0A

:: ===================================================
:: CONFIG
:: ===================================================

set PROJECT_PATH=C:\hk\generator

:: Recommended smaller model
set MODEL=ollama/qwen2.5:3b

:: ===================================================
:: OLLAMA OPTIMIZATION
:: ===================================================

set OLLAMA_KEEP_ALIVE=24h
set OLLAMA_NUM_CTX=2048
set OLLAMA_NUM_GPU=0

:: ===================================================
:: FREE RAM
:: ===================================================

echo ===================================================
echo   FREEING SYSTEM MEMORY
echo ===================================================

echo.
echo [1/8] Stopping old Ollama sessions...

ollama stop deepseek-r1:7b >nul 2>&1
ollama stop deepseek-r1:1.5b >nul 2>&1
ollama stop qwen2.5-coder:1.5b >nul 2>&1

echo [2/8] Closing Brave Browser...
taskkill /F /IM brave.exe >nul 2>&1

echo [3/8] Closing VS Code...
taskkill /F /IM Code.exe >nul 2>&1

echo [4/8] Closing WhatsApp...
taskkill /F /IM WhatsApp.exe >nul 2>&1

echo [5/8] Closing Docker Desktop...
taskkill /F /IM "Docker Desktop.exe" >nul 2>&1
taskkill /F /IM com.docker.backend.exe >nul 2>&1
taskkill /F /IM com.docker.build.exe >nul 2>&1

echo [6/8] Closing Claude...
taskkill /F /IM Claude.exe >nul 2>&1

echo [7/8] Waiting for RAM cleanup...
timeout /t 5 /nobreak >nul

echo [8/8] RAM optimization complete.
echo.

:: ===================================================
:: OPEN PROJECT
:: ===================================================

echo ===================================================
echo   STARTING AIDER
echo ===================================================

echo Project: %PROJECT_PATH%
echo Model:   %MODEL%
echo.

cd /d "%PROJECT_PATH%"

if %errorlevel% neq 0 (
    echo [ERROR] Could not find:
    echo %PROJECT_PATH%
    pause
    exit /b
)

:: ===================================================
:: START AIDER
:: ===================================================

aider --model %MODEL% --architect

echo.
echo ===================================================
echo   SESSION CLOSED
echo ===================================================

pause