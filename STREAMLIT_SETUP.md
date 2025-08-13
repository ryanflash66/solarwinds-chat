# 🚀 SolarWinds IT Assistant - Streamlit Frontend Setup

## Quick Start Guide

### Prerequisites

- Python 3.10+
- SolarWinds chatbot backend (already built)
- Terminal/PowerShell

---

## 🔧 Setup Instructions

### 1. Install Dependencies

```powershell
# Install the new dependencies (Streamlit + requests)
uv sync
```

### 2. Start the Backend (FastAPI)

```powershell
# Terminal 1: Start the FastAPI backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start the Frontend (Streamlit)

```powershell
# Terminal 2: Start the Streamlit frontend
uv run streamlit run streamlit_app.py
```

---

## 🌐 Access URLs

- **Streamlit Frontend**: http://localhost:8501
- **FastAPI Backend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## 🎯 Features

### ✅ **Core Chat Interface**

- Real-time AI-powered IT support chat
- Source documentation display
- Response time tracking
- Chat history management

### ✅ **System Monitoring**

- Real-time health status
- Component status monitoring
- System metrics (CPU, Memory, Disk)
- API connectivity status

### ✅ **Advanced Features**

- SolarWinds solution search
- Configurable API endpoints
- Professional UI with status badges
- Mobile-responsive design

### ✅ **IT Staff Focused**

- Responses tailored for IT professionals
- SolarWinds documentation integration
- Quick action buttons
- Professional color scheme

---

## 🧪 Testing the Integration

### 1. **Health Check Test**

1. Open Streamlit at http://localhost:8501
2. In the sidebar, click "🔄 Refresh Status"
3. Should show "✅ System Online" if backend is running

### 2. **Chat Test**

1. Type in the chat: "How do I reset a user password?"
2. Should get an AI response (or fallback response)
3. Check response time and source display

### 3. **Search Test**

1. Click "🔍 Search Solutions"
2. Search for "printer issues"
3. Should return relevant results (if any data is indexed)

### 4. **Metrics Test**

1. Click "📊 System Metrics"
2. Should show CPU, memory, and application metrics

---

## 🔧 Configuration

### API Base URL

- Default: `http://localhost:8000`
- Change in sidebar: Settings → API Configuration
- For production: Update to your deployed FastAPI URL

### CORS Settings

The backend now supports:

- `http://localhost:8501` (Streamlit local)
- `https://*.streamlit.app` (Streamlit Cloud)
- `http://localhost:3000` (Next.js if needed later)

---

## 🚀 Deployment Options

### Streamlit Cloud (Free)

1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Connect your repository
4. Set environment variables:
   - `API_BASE_URL=https://your-fastapi-deployment.com`

### Local Network Access

```powershell
# Make Streamlit accessible on network
uv run streamlit run streamlit_app.py --server.address 0.0.0.0
```

---

## 🐛 Troubleshooting

### "System Offline" Error

1. Make sure FastAPI is running on port 8000
2. Check the API URL in Streamlit settings
3. Verify CORS settings in `app/core/config.py`

### Connection Refused

1. Ensure both services are running
2. Check firewall/antivirus blocking ports
3. Try restarting both services

### LLM Not Working

1. The system uses fallback responses by default
2. To enable AI: Configure OLLAMA or OpenRouter API keys
3. Check health status for LLM service status

---

## 🎉 What's New vs. Original Plan

### ✅ **Faster Development**

- No HTML/CSS/JavaScript needed
- Built-in responsive design
- Professional UI components

### ✅ **Better for IT Staff**

- Clean, data-focused interface
- Real-time status monitoring
- Easy deployment options

### ✅ **Same Backend Power**

- All FastAPI features work unchanged
- LLM integration (OpenRouter/OLLAMA)
- Vector search with Chroma
- Background SolarWinds sync

---

## 📚 Next Steps

1. **Test the basic functionality** (chat, health check)
2. **Configure LLM provider** (OLLAMA or OpenRouter)
3. **Add SolarWinds API credentials** for real data
4. **Deploy to Streamlit Cloud** for team access
5. **Customize UI** colors/branding if needed

**Your FastAPI backend is 100% ready for Streamlit!** 🎊
