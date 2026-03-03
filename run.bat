@echo off
SETLOCAL EnableDelayedExpansion

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.11 or newer.
    pause
    exit /b 1
)

:: 2. Check and Setup Virtual Environment
if not exist ".venv" (
    echo [INFO] Virtual environment not found. Initializing setup...
    python scripts/bootstrap.py
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to set up virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Check and Setup .env file
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example...
        copy .env.example .env >nul
    ) else (
        echo [WARNING] .env.example not found. Creating a blank .env...
        echo BING_API_KEY=> .env
        echo BING_ENDPOINT=https://api.bing.microsoft.com/v7.0/images/search>> .env
    )
)

:: 4. Run the application
echo [INFO] Starting Auto Product Image Downloader...
.venv\Scripts\python.exe -m imggen_app.main

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application crashed or was closed unexpectedly (Code: %errorlevel%).
    pause
)
