"""LLM service with support for OpenRouter and OLLAMA providers."""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from enum import Enum

import httpx
import ollama
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.models.schemas import SourceDoc

logger = get_logger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers."""
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_response(
        self, 
        prompt: str, 
        sources: List[SourceDoc],
        stream: bool = False
    ) -> str:
        """Generate a response using the LLM."""
        pass
    
    @abstractmethod
    async def generate_response_stream(
        self, 
        prompt: str, 
        sources: List[SourceDoc]
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using the LLM."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM provider is available."""
        pass


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter LLM provider for cloud-based models."""
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.model = settings.openrouter_model
        
    async def initialize(self) -> None:
        """Initialize the OpenRouter client."""
        if not settings.openrouter_api_key:
            raise LLMError("OpenRouter API key not configured")
            
        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        logger.info(f"OpenRouter provider initialized with model: {self.model}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(
        self, 
        prompt: str, 
        sources: List[SourceDoc],
        stream: bool = False
    ) -> str:
        """Generate a response using OpenRouter."""
        if not self.client:
            await self.initialize()
        
        try:
            messages = [
                {"role": "system", "content": self._create_system_prompt()},
                {"role": "user", "content": self._format_prompt_with_sources(prompt, sources)}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
                stream=stream
            )
            
            if stream:
                return response  # Return the stream object for streaming responses
            else:
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"OpenRouter error: {str(e)}")
            raise LLMError(f"OpenRouter generation failed: {str(e)}")
    
    async def generate_response_stream(
        self, 
        prompt: str, 
        sources: List[SourceDoc]
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using OpenRouter."""
        if not self.client:
            await self.initialize()
        
        try:
            messages = [
                {"role": "system", "content": self._create_system_prompt()},
                {"role": "user", "content": self._format_prompt_with_sources(prompt, sources)}
            ]
            
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenRouter streaming error: {str(e)}")
            raise LLMError(f"OpenRouter streaming failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check OpenRouter availability."""
        try:
            if not self.client:
                await self.initialize()
            
            # Simple test call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"OpenRouter health check failed: {str(e)}")
            return False
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for IT staff assistance."""
        return """You are an AI assistant helping IT staff resolve user issues using SolarWinds knowledge base solutions.

Your role:
- Help IT staff find solutions to resolve user problems
- Provide step-by-step guidance for IT staff to assist users
- Reference relevant SolarWinds documentation when available
- Focus on practical resolution steps for IT professionals

Guidelines:
- Frame responses for IT staff, not end users
- Include troubleshooting steps IT staff can follow
- Mention when issues might need escalation
- Keep responses professional and concise
- Always cite sources when using SolarWinds documentation"""
    
    def _format_prompt_with_sources(self, prompt: str, sources: List[SourceDoc]) -> str:
        """Format the user prompt with relevant sources."""
        if not sources:
            return f"""Query: {prompt}

No specific SolarWinds documentation found for this query. Please provide general IT guidance for this issue."""
        
        sources_text = "\n\n".join([
            f"Source {i+1} (ID: {source.id}): {source.title}\n{getattr(source, 'content', 'No content available')}"
            for i, source in enumerate(sources)
        ])
        
        return f"""Query: {prompt}

Relevant SolarWinds Documentation:
{sources_text}

Based on the above documentation, provide IT staff guidance for resolving this issue."""


class OLLAMAProvider(BaseLLMProvider):
    """OLLAMA provider for local LLM models."""
    
    def __init__(self):
        self.client = None
        self.model = settings.ollama_model
        self.base_url = settings.ollama_base_url
        
    async def initialize(self) -> None:
        """Initialize the OLLAMA client."""
        try:
            # OLLAMA client is synchronous, so we'll use it in a thread pool
            self.client = ollama.Client(host=self.base_url)
            
            # Check if model is available
            models = await asyncio.get_event_loop().run_in_executor(
                None, self.client.list
            )
            
            model_names = [m['name'] for m in models.get('models', [])]
            if self.model not in model_names:
                logger.warning(f"Model {self.model} not found. Available: {model_names}")
                # Try to pull the model
                await asyncio.get_event_loop().run_in_executor(
                    None, self.client.pull, self.model
                )
            
            logger.info(f"OLLAMA provider initialized with model: {self.model}")
            
        except Exception as e:
            raise LLMError(f"OLLAMA initialization failed: {str(e)}")
    
    async def generate_response(
        self, 
        prompt: str, 
        sources: List[SourceDoc],
        stream: bool = False
    ) -> str:
        """Generate a response using OLLAMA."""
        if not self.client:
            await self.initialize()
        
        try:
            formatted_prompt = self._format_prompt_with_sources(prompt, sources)
            
            # Run OLLAMA in thread pool since it's synchronous
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.generate(
                    model=self.model,
                    prompt=formatted_prompt,
                    stream=stream
                )
            )
            
            if stream:
                return response  # Return generator for streaming
            else:
                return response.get('response', '')
                
        except Exception as e:
            logger.error(f"OLLAMA error: {str(e)}")
            raise LLMError(f"OLLAMA generation failed: {str(e)}")
    
    async def generate_response_stream(
        self, 
        prompt: str, 
        sources: List[SourceDoc]
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using OLLAMA."""
        if not self.client:
            await self.initialize()
        
        try:
            formatted_prompt = self._format_prompt_with_sources(prompt, sources)
            
            # OLLAMA streaming is more complex with async execution
            def generate_stream():
                return self.client.generate(
                    model=self.model,
                    prompt=formatted_prompt,
                    stream=True
                )
            
            # Run in thread pool and yield chunks
            stream = await asyncio.get_event_loop().run_in_executor(None, generate_stream)
            
            for chunk in stream:
                if chunk.get('response'):
                    yield chunk['response']
                    
        except Exception as e:
            logger.error(f"OLLAMA streaming error: {str(e)}")
            raise LLMError(f"OLLAMA streaming failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check OLLAMA availability."""
        try:
            if not self.client:
                await self.initialize()
            
            # Simple test generation
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.generate(
                    model=self.model,
                    prompt="test",
                    options={"num_predict": 1}
                )
            )
            return True
        except Exception as e:
            logger.warning(f"OLLAMA health check failed: {str(e)}")
            return False
    
    def _format_prompt_with_sources(self, prompt: str, sources: List[SourceDoc]) -> str:
        """Format the user prompt with relevant sources for OLLAMA."""
        system_prompt = """You are an AI assistant helping IT staff resolve user issues using SolarWinds knowledge base solutions.

Your role:
- Help IT staff find solutions to resolve user problems
- Provide step-by-step guidance for IT staff to assist users
- Reference relevant SolarWinds documentation when available
- Focus on practical resolution steps for IT professionals

Guidelines:
- Frame responses for IT staff, not end users
- Include troubleshooting steps IT staff can follow
- Mention when issues might need escalation
- Keep responses professional and concise
- Always cite sources when using SolarWinds documentation

"""
        
        if not sources:
            return f"""{system_prompt}

Query: {prompt}

No specific SolarWinds documentation found for this query. Please provide general IT guidance for this issue."""
        
        sources_text = "\n\n".join([
            f"Source {i+1} (ID: {source.id}): {source.title}\n{getattr(source, 'content', 'No content available')}"
            for i, source in enumerate(sources)
        ])
        
        return f"""{system_prompt}

Query: {prompt}

Relevant SolarWinds Documentation:
{sources_text}

Based on the above documentation, provide IT staff guidance for resolving this issue."""


class LLMService:
    """Main LLM service that manages different providers."""
    
    def __init__(self):
        self.provider: Optional[BaseLLMProvider] = None
        self.provider_type: Optional[LLMProvider] = None
        
    async def initialize(self) -> None:
        """Initialize the LLM service with the configured provider."""
        provider_name = settings.llm_provider.lower()
        
        if provider_name == LLMProvider.OPENROUTER:
            self.provider = OpenRouterProvider()
            self.provider_type = LLMProvider.OPENROUTER
        elif provider_name == LLMProvider.OLLAMA:
            self.provider = OLLAMAProvider()
            self.provider_type = LLMProvider.OLLAMA
        else:
            raise LLMError(f"Unknown LLM provider: {provider_name}")
        
        await self.provider.initialize()
        logger.info(f"LLM service initialized with provider: {self.provider_type}")
    
    async def generate_response(
        self, 
        query: str, 
        sources: List[SourceDoc],
        stream: bool = False
    ) -> str:
        """Generate a response for the given query and sources."""
        if not self.provider:
            await self.initialize()
        
        logger.info(f"Generating LLM response for query with {len(sources)} sources")
        
        try:
            response = await self.provider.generate_response(query, sources, stream)
            logger.info("LLM response generated successfully")
            return response
        except Exception as e:
            logger.error(f"LLM response generation failed: {str(e)}")
            raise
    
    async def generate_response_stream(
        self, 
        query: str, 
        sources: List[SourceDoc]
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response for the given query and sources."""
        if not self.provider:
            await self.initialize()
        
        logger.info(f"Generating streaming LLM response for query with {len(sources)} sources")
        
        try:
            async for chunk in self.provider.generate_response_stream(query, sources):
                yield chunk
        except Exception as e:
            logger.error(f"LLM streaming response failed: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the LLM service."""
        if not self.provider:
            try:
                await self.initialize()
            except Exception as e:
                return {
                    "provider": settings.llm_provider,
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        try:
            is_healthy = await self.provider.health_check()
            return {
                "provider": self.provider_type,
                "status": "healthy" if is_healthy else "unhealthy",
                "model": getattr(self.provider, 'model', 'unknown')
            }
        except Exception as e:
            return {
                "provider": self.provider_type,
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Clean up the LLM service."""
        if self.provider:
            # Close any open connections
            if hasattr(self.provider, 'client') and hasattr(self.provider.client, 'close'):
                await self.provider.client.close()
        
        logger.info("LLM service cleaned up")


# Global LLM service instance
llm_service = LLMService()