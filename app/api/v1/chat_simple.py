"""Simplified chat endpoints for quick startup."""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ChatRequest, ChatResponse, SourceDoc
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Simplified chat endpoint that works without heavy services.
    
    This version provides fallback responses while the full system loads.
    """
    start_time = time.time()
    query_id = str(uuid.uuid4())
    
    try:
        logger.info(f"Chat request received (simple mode)", extra={
            "query_id": query_id,
            "query": request.query[:100] + "..." if len(request.query) > 100 else request.query,
        })
        
        # Generate a helpful fallback response
        answer = generate_simple_response(request.query)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        response = ChatResponse(
            answer=answer,
            sources=[],  # No sources in simple mode
            query_id=query_id,
            response_time_ms=response_time_ms,
        )
        
        logger.info(f"Chat response generated (simple mode)", extra={
            "query_id": query_id,
            "response_time_ms": response_time_ms,
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", extra={
            "query_id": query_id,
            "query": request.query,
        })
        
        # Return error response
        return ChatResponse(
            answer="I'm sorry, but I'm currently starting up. Please try again in a moment, or check that all services are properly configured.",
            sources=[],
            query_id=query_id,
            response_time_ms=int((time.time() - start_time) * 1000),
        )


def generate_simple_response(query: str) -> str:
    """Generate a simple response based on keywords in the query."""
    query_lower = query.lower()
    
    # Simple keyword-based responses
    if any(word in query_lower for word in ["password", "reset", "login", "account"]):
        return """For password reset issues:
        
1. **Verify user identity** through secondary authentication
2. **Access Active Directory** Users and Computers console
3. **Navigate to the user account** in question
4. **Right-click the account** and select 'Reset Password'
5. **Generate a temporary secure password**
6. **Set 'User must change password at next logon'**
7. **Communicate the password securely** to the user
8. **Document the reset** in your ticketing system

⚠️ Note: This is a simplified response. For full AI-powered assistance with source citations, please ensure all services are running."""
    
    elif any(word in query_lower for word in ["printer", "print", "spooler"]):
        return """For printer connectivity issues:
        
1. **Check physical connections** (USB/Ethernet cables)
2. **Verify printer power** and display messages
3. **Test network connectivity** (for network printers)
4. **Check printer driver** installation and version
5. **Clear print queue** and restart print spooler service
6. **Verify printer sharing** settings if applicable
7. **Test with different user** to isolate permission issues
8. **Consider IP conflicts** for network printers

⚠️ Note: This is a simplified response. For full AI-powered assistance with source citations, please ensure all services are running."""
    
    elif any(word in query_lower for word in ["vpn", "connection", "network", "internet"]):
        return """For VPN/Network connection problems:
        
1. **Verify user credentials** and account status
2. **Check VPN client software** version and updates  
3. **Confirm firewall exceptions** and antivirus settings
4. **Test internet connectivity** without VPN
5. **Verify VPN server** address and port settings
6. **Check for conflicting** network adapters
7. **Review Windows Event Logs** for VPN errors
8. **Test alternative protocols** if available

⚠️ Note: This is a simplified response. For full AI-powered assistance with source citations, please ensure all services are running."""
    
    elif any(word in query_lower for word in ["email", "outlook", "exchange", "mail"]):
        return """For email client configuration:
        
**Outlook Setup:**
1. Open Outlook → File → Add Account
2. Enter user's email address
3. Use Auto Account Setup when possible
4. Manual setup if needed:
   - IMAP: server.company.com, port 993, SSL
   - SMTP: smtp.company.com, port 587, TLS
5. Test send/receive functionality

**Mobile Device:**
- Use Exchange ActiveSync settings
- Server: mail.company.com
- Enable SSL/TLS encryption

⚠️ Note: This is a simplified response. For full AI-powered assistance with source citations, please ensure all services are running."""
    
    else:
        return f"""I understand you're asking about: "{query}"

I'm currently running in simplified mode while the full AI system initializes. Here are some general IT troubleshooting steps:

**General Troubleshooting Process:**
1. **Identify the problem** - What specifically isn't working?
2. **Check recent changes** - Any software updates or configuration changes?
3. **Verify basics** - Power, connections, network connectivity
4. **Check logs** - Windows Event Viewer, application logs
5. **Test with different user** - Is it user-specific or system-wide?
6. **Research known issues** - Check vendor documentation
7. **Try standard fixes** - Restart services, clear caches
8. **Escalate if needed** - Document findings and escalate

⚠️ **Note:** This is a basic response. For full AI-powered assistance with:
- Semantic search through SolarWinds knowledge base
- Relevant source document citations  
- Detailed step-by-step guidance
- Real-time system integration

Please ensure all services are running properly, or try the Docker deployment for a complete setup."""