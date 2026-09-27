@echo off
title SmartBin Backend API (port 8000)
cd /d "C:\smb project\backend"
if not exist ".\venv\Scripts\python.exe" (
  echo ERROR: venv not found at "C:\smb project\backend\venv\Scripts\python.exe"
  pause
  exit /b 1
)
echo Starting SmartBin API on http://localhost:8000 ...
echo Keep this window open while you use the app.
echo.
".\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
echo.
echo API stopped.
pause