@echo off
echo Starting SolarWinds IT Solutions Chatbot Frontend...
echo Streamlit UI will be available at: http://localhost:8501
echo.
echo Make sure the backend is running first!
echo.
uv run python -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501