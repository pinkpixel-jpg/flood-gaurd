@echo off
title FloodGuard Frontend :8080
cd /d "%~dp0"
echo [FloodGuard frontend] http://localhost:8080  (keep this window open)
python scripts\serve_frontend.py
pause
