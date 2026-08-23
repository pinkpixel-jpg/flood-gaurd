@echo off
title FloodGuard AI - starting both servers
cd /d "%~dp0"
start "FloodGuard Backend" cmd /c start_backend.bat
timeout /t 2 /nobreak >nul
start "FloodGuard Frontend" cmd /c start_frontend.bat
echo.
echo  Both servers are starting in separate windows:
echo     Frontend : http://localhost:8080
echo     Backend  : http://localhost:8000/api/health
echo.
echo  Open http://localhost:8080 in your browser.
echo  Close the two server windows to stop the app.
start "" http://localhost:8080
