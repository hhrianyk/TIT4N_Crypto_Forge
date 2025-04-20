@echo off
echo Starting Crypto Payment System...

rem Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in the PATH.
    echo Please install Python and try again.
    pause
    exit /b 1
)

rem Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found. Creating...
    python -m venv venv
    call venv\Scripts\activate
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

rem Check if .env file exists
if not exist .env (
    echo .env file not found. Creating from example...
    copy .env.example .env
    echo Please edit the .env file with your configuration before continuing.
    notepad .env
)

echo Starting the application...
python start.py

pause 