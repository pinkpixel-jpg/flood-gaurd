@echo off
title FloodGuard Backend :8000
cd /d "%~dp0"
echo [FloodGuard backend] http://localhost:8000/api  (keep this window open)
python -m uvicorn src.delivery.api:app --host 127.0.0.1 --port 8000
pause
