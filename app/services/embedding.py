"""Embedding service with OpenAI and local Sentence-Transformers support."""

import asyncio
import hashlib
import json
import time
from typing import Dict, List, Optional, Any, Union
from concurrent.futures import ThreadPoolExecutor

import openai
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """Simple in-memory cache for embeddings."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, List[float]] = {}
        self.timestamps: Dict[str, float] = {}
        self.max_size = max_size
        
    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate cache key for text and model."""
        content = f"{model}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Get embedding from cache."""
        key = self._get_cache_key(text, model)
        return self.cache.get(key)
    
    def set(self, text: str, model: str, embedding: List[float]) -> None:
        """Store embedding in cache."""
        key = self._get_cache_key(text, model)
        
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.timestamps.keys(), key=self.timestamps.get)
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
        
        self.cache[key] = embedding
        self.timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        self.timestamps.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": getattr(self, "_hit_count", 0) / max(getattr(self, "_total_requests", 1), 1),
        }


class OpenAIEmbeddingProvider:
    """OpenAI embedding provider."""
    
    def __init__(self):
        self.client: Optional[openai.AsyncOpenAI] = None
        self.model = settings.embedding_model
        
    async def initialize(self) -> None:
        """Initialize the OpenAI client."""
        if not settings.openai_api_key:
            raise EmbeddingError("OpenAI API key not configured")
        
        self.client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=30.0,
        )
        
        logger.info(f"Initialized OpenAI embedding provider with model: {self.model}")
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text."""
        if not self.client:
            raise EmbeddingError("OpenAI client not initialized")
        
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(f"Generated OpenAI embedding", extra={
                "text_length": len(text),
                "embedding_dimension": len(embedding),
                "model": self.model,
            })
            
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {str(e)}")
            raise EmbeddingError(f"OpenAI embedding failed: {str(e)}")
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        if not self.client:
            raise EmbeddingError("OpenAI client not initialized")
        
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            
            embeddings = [item.embedding for item in response.data]
            
            logger.info(f"Generated {len(embeddings)} OpenAI embeddings in batch")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding error: {str(e)}")
            raise EmbeddingError(f"OpenAI batch embedding failed: {str(e)}")


class LocalEmbeddingProvider:
    """Local Sentence-Transformers embedding provider."""
    
    def __init__(self):
        self.model: Optional[SentenceTransformer] = None
        self.model_name = "all-MiniLM-L6-v2"  # Fast and efficient model
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    async def initialize(self) -> None:
        """Initialize the local model."""
        try:
            loop = asyncio.get_event_loop()
            
            # Load model in thread pool (it's CPU intensive)
            self.model = await loop.run_in_executor(
                self.executor,
                self._load_model
            )
            
            logger.info(f"Initialized local embedding provider with model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize local embedding model: {str(e)}")
            raise EmbeddingError(f"Local embedding initialization failed: {str(e)}")
    
    def _load_model(self) -> SentenceTransformer:
        """Load the Sentence-Transformers model (sync operation)."""
        return SentenceTransformer(self.model_name)
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text."""
        if not self.model:
            raise EmbeddingError("Local embedding model not initialized")
        
        try:
            loop = asyncio.get_event_loop()
            
            embedding = await loop.run_in_executor(
                self.executor,
                self._encode_text,
                text
            )
            
            logger.debug(f"Generated local embedding", extra={
                "text_length": len(text),
                "embedding_dimension": len(embedding),
                "model": self.model_name,
            })
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Local embedding error: {str(e)}")
            raise EmbeddingError(f"Local embedding failed: {str(e)}")
    
    def _encode_text(self, text: str):
        """Encode text using the model (sync operation)."""
        return self.model.encode(text)
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        if not self.model:
            raise EmbeddingError("Local embedding model not initialized")
        
        try:
            loop = asyncio.get_event_loop()
            
            embeddings = await loop.run_in_executor(
                self.executor,
                self._encode_texts_batch,
                texts
            )
            
            logger.info(f"Generated {len(embeddings)} local embeddings in batch")
            
            return [emb.tolist() for emb in embeddings]
            
        except Exception as e:
            logger.error(f"Local batch embedding error: {str(e)}")
            raise EmbeddingError(f"Local batch embedding failed: {str(e)}")
    
    def _encode_texts_batch(self, texts: List[str]):
        """Encode multiple texts using the model (sync operation)."""
        return self.model.encode(texts)
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.executor:
            self.executor.shutdown(wait=True)


class EmbeddingService:
    """Main embedding service with provider fallback and caching."""
    
    def __init__(self):
        self.openai_provider = OpenAIEmbeddingProvider()
        self.local_provider = LocalEmbeddingProvider()
        self.cache = EmbeddingCache()
        self.primary_provider = settings.embedding_provider
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the embedding service."""
        if self._initialized:
            return
        
        try:
            # Initialize primary provider
            if self.primary_provider == "openai" and settings.openai_api_key:
                try:
                    await self.openai_provider.initialize()
                    logger.info("Using OpenAI as primary embedding provider")
                except Exception as e:
                    logger.warning(f"OpenAI provider failed, falling back to local: {str(e)}")
                    await self.local_provider.initialize()
                    self.primary_provider = "local"
            else:
                await self.local_provider.initialize()
                self.primary_provider = "local"
                logger.info("Using local model as primary embedding provider")
            
            # Always initialize the fallback provider if possible
            if self.primary_provider == "openai":
                try:
                    await self.local_provider.initialize()
                    logger.info("Local provider initialized as fallback")
                except Exception as e:
                    logger.warning(f"Local provider initialization failed: {str(e)}")
            elif self.primary_provider == "local" and settings.openai_api_key:
                try:
                    await self.openai_provider.initialize()
                    logger.info("OpenAI provider initialized as fallback")
                except Exception as e:
                    logger.warning(f"OpenAI provider initialization failed: {str(e)}")
            
            self._initialized = True
            logger.info(f"Embedding service initialized with primary provider: {self.primary_provider}")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {str(e)}")
            raise EmbeddingError(f"Embedding service initialization failed: {str(e)}")
    
    async def get_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """
        Get embedding for a single text.
        
        Args:
            text: Text to embed
            use_cache: Whether to use caching
            
        Returns:
            Embedding vector
        """
        if not self._initialized:
            await self.initialize()
        
        # Clean and validate text
        text = text.strip()
        if not text:
            raise EmbeddingError("Empty text provided for embedding")
        
        # Check cache first
        if use_cache:
            cached_embedding = self.cache.get(text, self.primary_provider)
            if cached_embedding:
                return cached_embedding
        
        # Try primary provider
        try:
            embedding = await self._get_embedding_with_provider(text, self.primary_provider)
            
            # Cache the result
            if use_cache:
                self.cache.set(text, self.primary_provider, embedding)
            
            return embedding
            
        except Exception as e:
            logger.warning(f"Primary provider ({self.primary_provider}) failed: {str(e)}")
            
            # Try fallback provider
            fallback_provider = "local" if self.primary_provider == "openai" else "openai"
            try:
                embedding = await self._get_embedding_with_provider(text, fallback_provider)
                
                # Cache with fallback provider model name
                if use_cache:
                    self.cache.set(text, fallback_provider, embedding)
                
                logger.info(f"Successfully used fallback provider: {fallback_provider}")
                return embedding
                
            except Exception as fallback_error:
                logger.error(f"Both providers failed. Primary: {str(e)}, Fallback: {str(fallback_error)}")
                raise EmbeddingError(f"All embedding providers failed: {str(e)}")
    
    async def _get_embedding_with_provider(self, text: str, provider: str) -> List[float]:
        """Get embedding using a specific provider."""
        if provider == "openai":
            return await self.openai_provider.get_embedding(text)
        elif provider == "local":
            return await self.local_provider.get_embedding(text)
        else:
            raise EmbeddingError(f"Unknown provider: {provider}")
    
    async def get_embeddings_batch(
        self, 
        texts: List[str], 
        use_cache: bool = True,
        batch_size: int = 50
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            use_cache: Whether to use caching
            batch_size: Maximum batch size for API calls
            
        Returns:
            List of embedding vectors
        """
        if not self._initialized:
            await self.initialize()
        
        if not texts:
            return []
        
        # Clean texts
        texts = [text.strip() for text in texts if text.strip()]
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Check cache for batch items
            batch_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            if use_cache:
                for j, text in enumerate(batch):
                    cached = self.cache.get(text, self.primary_provider)
                    if cached:
                        batch_embeddings.append((j, cached))
                    else:
                        uncached_texts.append(text)
                        uncached_indices.append(j)
            else:
                uncached_texts = batch
                uncached_indices = list(range(len(batch)))
            
            # Get embeddings for uncached texts
            if uncached_texts:
                try:
                    new_embeddings = await self._get_embeddings_batch_with_provider(
                        uncached_texts, self.primary_provider
                    )
                    
                    # Cache new embeddings
                    if use_cache:
                        for text, embedding in zip(uncached_texts, new_embeddings):
                            self.cache.set(text, self.primary_provider, embedding)
                    
                    # Add to batch results
                    for idx, embedding in zip(uncached_indices, new_embeddings):
                        batch_embeddings.append((idx, embedding))
                        
                except Exception as e:
                    logger.warning(f"Batch embedding failed with primary provider: {str(e)}")
                    
                    # Try fallback provider
                    fallback_provider = "local" if self.primary_provider == "openai" else "openai"
                    try:
                        new_embeddings = await self._get_embeddings_batch_with_provider(
                            uncached_texts, fallback_provider
                        )
                        
                        # Cache with fallback provider
                        if use_cache:
                            for text, embedding in zip(uncached_texts, new_embeddings):
                                self.cache.set(text, fallback_provider, embedding)
                        
                        # Add to batch results
                        for idx, embedding in zip(uncached_indices, new_embeddings):
                            batch_embeddings.append((idx, embedding))
                            
                        logger.info(f"Successfully used fallback provider for batch: {fallback_provider}")
                        
                    except Exception as fallback_error:
                        logger.error(f"Batch embedding failed with both providers: {str(e)}, {str(fallback_error)}")
                        raise EmbeddingError(f"Batch embedding failed: {str(e)}")
            
            # Sort batch embeddings by original index and extract embeddings
            batch_embeddings.sort(key=lambda x: x[0])
            embeddings.extend([emb for _, emb in batch_embeddings])
        
        logger.info(f"Generated {len(embeddings)} embeddings in batch")
        return embeddings
    
    async def _get_embeddings_batch_with_provider(
        self, 
        texts: List[str], 
        provider: str
    ) -> List[List[float]]:
        """Get batch embeddings using a specific provider."""
        if provider == "openai":
            return await self.openai_provider.get_embeddings_batch(texts)
        elif provider == "local":
            return await self.local_provider.get_embeddings_batch(texts)
        else:
            raise EmbeddingError(f"Unknown provider: {provider}")
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get information about the embedding service."""
        return {
            "primary_provider": self.primary_provider,
            "openai_available": self.openai_provider.client is not None,
            "local_available": self.local_provider.model is not None,
            "cache_stats": self.cache.get_stats(),
            "embedding_dimension": settings.embedding_dimension,
            "initialized": self._initialized,
        }
    
    async def cleanup(self) -> None:
        """Cleanup service resources."""
        try:
            self.local_provider.cleanup()
            self.cache.clear()
            logger.info("Embedding service cleaned up")
        except Exception as e:
            logger.error(f"Error during embedding service cleanup: {str(e)}")


# Global service instance
embedding_service = EmbeddingService()