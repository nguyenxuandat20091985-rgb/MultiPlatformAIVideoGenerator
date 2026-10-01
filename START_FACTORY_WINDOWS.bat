@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher not found. Install Python 3.11+ from python.org.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating project virtual environment...
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo Could not create Python 3.11 environment. Check Python installation.
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\uvicorn.exe" (
  echo Installing Python dependencies. This may take several minutes...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Dependency installation failed. Review the error above.
    pause
    exit /b 1
  )
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg is not installed or is not on PATH. Install FFmpeg, reopen this window, and retry.
  pause
  exit /b 1
)

if not exist ".env" if exist ".env.example" (
  copy ".env.example" ".env" >nul
  echo Created .env from template. Add optional provider keys there if needed.
)

echo Starting local API on 127.0.0.1:8000
echo Keep this window open while using the factory.
".venv\Scripts\python.exe" -m uvicorn api:app --host 127.0.0.1 --port 8000
pause
