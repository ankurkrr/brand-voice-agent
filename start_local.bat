@echo off
echo ============================================================
echo Starting Voice Meta Agent - Local Development
echo ============================================================

echo.
echo.
echo [1/3] Skipping Database Check (Assumed Initialized)

echo.
echo [2/3] Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo [3/3] Starting FastAPI server...
echo.
echo API will be available at: http://localhost:8082
echo Press Ctrl+C to stop the server
echo.

set ENV=local
python -m uvicorn adapters.api.main:app --port 8082 --reload --log-level debug
