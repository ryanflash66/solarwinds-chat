# 🚀 Quick Start Guide

## **The Fix for "Failed to canonicalize script path" Error**

Use `python -m` instead of direct commands with `uv run`:

## ✅ **Corrected Commands:**

### **Option 1: Manual Commands**
```powershell
# Terminal 1: Start Backend
uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Frontend  
uv run python -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

### **Option 2: Use the Batch Scripts** 
```powershell
# Terminal 1: Double-click or run
start_backend.bat

# Terminal 2: Double-click or run  
start_frontend.bat
```

### **Option 3: Docker (All-in-One)**
```powershell
docker-compose up -d
```

## 🌐 **Access Your Application:**

- **🎨 Streamlit Frontend**: http://localhost:8501 *(Main User Interface)*
- **🔧 API Backend**: http://localhost:8000 *(Developer API)*  
- **📚 API Documentation**: http://localhost:8000/docs *(Interactive API Docs)*

## 🧪 **Test the System:**

```powershell
# Run end-to-end system test
uv run python test_system.py
```

## ❓ **Troubleshooting:**

### **"Failed to canonicalize script path"**
- ✅ **Solution**: Use `uv run python -m [command]` instead of `uv run [command]`
- ✅ **Root cause**: Windows path resolution issue with uv

### **"Connection refused" errors**
- Make sure backend is running first (Terminal 1)
- Then start frontend (Terminal 2)
- Wait 10-15 seconds for services to fully initialize

### **"No module named 'app'"**
- Make sure you're in the correct directory: `R:\Dropbox\_Code\solarwinds_chat`
- Check that `app/` directory exists with `main.py` inside

## 🎉 **You're Ready!**

The system is fully functional with:
- ✅ AI-powered IT support chat
- ✅ 25 realistic mock solutions  
- ✅ Vector semantic search
- ✅ Professional web interface
- ✅ Real-time health monitoring
- ✅ Production-ready Docker deployment

**Start chatting at**: http://localhost:8501 🚀