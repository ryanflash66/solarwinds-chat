@echo off
echo Starting SolarWinds IT Solutions Chatbot Backend...
echo API will be available at: http://localhost:8000
echo API Documentation at: http://localhost:8000/docs
echo.
uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000