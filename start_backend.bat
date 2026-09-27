@echo off
title SmartBin Backend API (port 8000)
cd /d "%~dp0backend"
if exist ".\venv\Scripts\python.exe" (
  set "PY_EXE=.\venv\Scripts\python.exe"
) else (
  set "PY_EXE=python"
)

echo Starting SmartBin API on http://localhost:8000 ...
echo Keep this window open while you use the app.
echo.
%PY_EXE% -m uvicorn app.main:app --host 0.0.0.0 --port 8000
echo.
echo API stopped.
pause