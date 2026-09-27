@echo off
title SmartBin Frontend (port 3000)
cd /d "C:\smb project\frontend"
echo Starting SmartBin web app on http://localhost:3000 ...
echo Keep this window open while you use the app.
echo.
where python >nul 2>nul
if errorlevel 1 (
  py -3 -m http.server 3000
) else (
  python -m http.server 3000
)
echo.
echo Server stopped.
pause