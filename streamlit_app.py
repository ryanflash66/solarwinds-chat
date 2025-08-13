"""
SolarWinds IT Solutions Chatbot - Streamlit Frontend
Helping IT staff resolve user issues quickly with AI-powered assistance.
"""

import streamlit as st
import requests
import json
import time
from typing import Dict, Any, List, Optional

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="SolarWinds IT Assistant",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-healthy {
        color: #28a745;
        font-weight: bold;
    }
    .status-unhealthy {
        color: #dc3545;
        font-weight: bold;
    }
    .status-disabled {
        color: #ffc107;
        font-weight: bold;
    }
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #ddd;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
    }
    .source-card {
        background-color: #e9ecef;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 0.25rem;
        border-left: 3px solid #007bff;
    }
</style>
""", unsafe_allow_html=True)

def check_api_health() -> Dict[str, Any]:
    """Check the health of the FastAPI backend."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"status": "unhealthy", "error": str(e)}

def send_chat_message(query: str) -> Dict[str, Any]:
    """Send a chat message to the FastAPI backend."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/chat",
            json={"query": query},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "answer": f"Error: Unable to get response (HTTP {response.status_code})",
                "sources": [],
                "query_id": "error",
                "response_time_ms": 0
            }
    except requests.exceptions.RequestException as e:
        return {
            "answer": f"Connection error: {str(e)}. Make sure the FastAPI server is running on {API_BASE_URL}",
            "sources": [],
            "query_id": "error",
            "response_time_ms": 0
        }

def search_solutions(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for solutions using the FastAPI backend."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/solutions/search",
            params={"q": query, "limit": limit},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except requests.exceptions.RequestException:
        return []

def get_system_metrics() -> Optional[Dict[str, Any]]:
    """Get system metrics from the FastAPI backend."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/metrics", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def format_status_badge(status: str) -> str:
    """Format a status badge with appropriate styling."""
    if status == "healthy":
        return f'<span class="status-healthy">● {status.upper()}</span>'
    elif status == "unhealthy":
        return f'<span class="status-unhealthy">● {status.upper()}</span>'
    else:
        return f'<span class="status-disabled">● {status.upper()}</span>'

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_status" not in st.session_state:
    st.session_state.api_status = None

# Header
st.markdown('<h1 class="main-header">🔧 SolarWinds IT Assistant</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">AI-powered support for IT staff to resolve user issues quickly</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("System Status")
    
    # Check API health
    if st.button("🔄 Refresh Status", use_container_width=True):
        with st.spinner("Checking system status..."):
            st.session_state.api_status = check_api_health()
    
    # Display health status
    if st.session_state.api_status:
        health_data = st.session_state.api_status
        
        if health_data.get("status") == "healthy":
            st.success("✅ System Online")
            
            # Show component status
            components = health_data.get("components", {})
            st.subheader("Components")
            
            for component, info in components.items():
                status = info.get("status", "unknown")
                message = info.get("message", "No details")
                
                st.markdown(
                    f"**{component.replace('_', ' ').title()}**: {format_status_badge(status)}",
                    unsafe_allow_html=True
                )
                st.caption(message)
                st.markdown("---")
                
        else:
            st.error("❌ System Offline")
            if "error" in health_data:
                st.error(f"Error: {health_data['error']}")
    else:
        st.warning("⚠️ Status Unknown")
        st.caption("Click 'Refresh Status' to check system health")
    
    # Settings section
    st.header("Settings")
    
    # API Configuration
    with st.expander("🔧 API Configuration", expanded=False):
        api_url = st.text_input("API Base URL", value=API_BASE_URL)
        if api_url != API_BASE_URL:
            st.warning("Restart the app to apply URL changes")
        
        st.caption("Default: http://localhost:8000")
    
    # About section
    with st.expander("ℹ️ About", expanded=False):
        st.markdown("""
        **SolarWinds IT Assistant** helps IT staff resolve user issues quickly using:
        
        - 🤖 **AI-Powered Responses** (OpenRouter/OLLAMA)
        - 📚 **SolarWinds Knowledge Base** 
        - 🔍 **Semantic Search** with vector embeddings
        - ⚡ **Real-time Processing** with FastAPI
        
        Built with: FastAPI, Streamlit, Chroma, OpenAI
        """)

# Main chat interface
st.header("💬 IT Support Chat")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show sources if available
        if message["role"] == "assistant" and "sources" in message:
            sources = message["sources"]
            if sources:
                with st.expander(f"📚 Related Documentation ({len(sources)} sources)"):
                    for i, source in enumerate(sources, 1):
                        st.markdown(f"""
                        <div class="source-card">
                            <strong>{i}. {source.get('title', 'Unknown Title')}</strong><br>
                            <small>ID: {source.get('id', 'N/A')} | Relevance: {source.get('score', 0):.2f}</small>
                        </div>
                        """, unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("How can I help you resolve an IT issue?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Searching SolarWinds knowledge base and generating response..."):
            response_data = send_chat_message(prompt)
            
            # Display the response
            answer = response_data.get("answer", "No response received")
            st.markdown(answer)
            
            # Show response metadata
            response_time = response_data.get("response_time_ms", 0)
            query_id = response_data.get("query_id", "unknown")
            
            st.caption(f"Response time: {response_time}ms | Query ID: {query_id}")
            
            # Show sources
            sources = response_data.get("sources", [])
            if sources:
                with st.expander(f"📚 Related Documentation ({len(sources)} sources)"):
                    for i, source in enumerate(sources, 1):
                        st.markdown(f"""
                        <div class="source-card">
                            <strong>{i}. {source.get('title', 'Unknown Title')}</strong><br>
                            <small>ID: {source.get('id', 'N/A')} | Relevance: {source.get('score', 0):.2f}</small>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Add assistant response to chat history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": answer,
                "sources": sources
            })

# Additional features
st.markdown("---")

# Quick actions
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔍 Search Solutions", use_container_width=True):
        st.session_state.show_search = True

with col2:
    if st.button("📊 System Metrics", use_container_width=True):
        st.session_state.show_metrics = True

with col3:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Show search interface
if st.session_state.get("show_search", False):
    st.header("🔍 Solution Search")
    
    search_query = st.text_input("Search SolarWinds solutions:", placeholder="e.g., password reset, printer issues")
    search_limit = st.slider("Number of results:", 1, 20, 5)
    
    if st.button("Search") and search_query:
        with st.spinner("Searching..."):
            results = search_solutions(search_query, search_limit)
            
            if results:
                st.success(f"Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    with st.expander(f"{i}. {result.get('title', 'Unknown Title')}"):
                        st.write(f"**ID:** {result.get('id', 'N/A')}")
                        st.write(f"**Score:** {result.get('score', 0):.3f}")
                        if 'content' in result:
                            st.write("**Content:**")
                            st.text(result['content'][:500] + "..." if len(result.get('content', '')) > 500 else result.get('content', ''))
            else:
                st.warning("No results found. Try a different search term.")
    
    if st.button("Close Search"):
        st.session_state.show_search = False
        st.rerun()

# Show metrics
if st.session_state.get("show_metrics", False):
    st.header("📊 System Metrics")
    
    metrics = get_system_metrics()
    if metrics:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Application Metrics")
            app_metrics = metrics.get("application", {})
            
            st.metric("Uptime", f"{app_metrics.get('uptime_seconds', 0):.0f}s")
            st.metric("Total Requests", app_metrics.get("total_requests", 0))
            st.metric("Active Connections", app_metrics.get("active_connections", 0))
        
        with col2:
            st.subheader("System Metrics")
            sys_metrics = metrics.get("system", {})
            
            st.metric("CPU Usage", f"{sys_metrics.get('cpu_percent', 0):.1f}%")
            st.metric("Memory Usage", f"{sys_metrics.get('memory_percent', 0):.1f}%")
            st.metric("Disk Usage", f"{sys_metrics.get('disk_percent', 0):.1f}%")
    else:
        st.error("Unable to fetch system metrics")
    
    if st.button("Close Metrics"):
        st.session_state.show_metrics = False
        st.rerun()

# Footer
st.markdown("---")
st.caption("SolarWinds IT Assistant | Built with FastAPI + Streamlit | For IT Staff Use Only")