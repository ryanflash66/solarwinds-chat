"""Vector store service using Chroma for semantic search and document storage."""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.exceptions import VectorStoreError
from app.core.logging import get_logger
from app.models.schemas import SolutionRecord, SourceDoc

logger = get_logger(__name__)


class VectorStoreService:
    """Service for managing the Chroma vector database."""
    
    def __init__(self):
        self.client: Optional[chromadb.ClientAPI] = None
        self.collection: Optional[Collection] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def connect(self) -> None:
        """Connect to Chroma database."""
        try:
            # Run Chroma operations in thread pool (it's not fully async)
            loop = asyncio.get_event_loop()
            
            # Create Chroma client
            self.client = await loop.run_in_executor(
                self.executor,
                self._create_client
            )
            
            # Get or create collection
            self.collection = await loop.run_in_executor(
                self.executor,
                self._get_or_create_collection
            )
            
            logger.info("Successfully connected to Chroma vector store", extra={
                "collection_name": settings.chroma_collection_name,
                "host": settings.chroma_host,
                "port": settings.chroma_port,
            })
            
        except Exception as e:
            logger.error(f"Failed to connect to Chroma: {str(e)}")
            raise VectorStoreError(f"Chroma connection failed: {str(e)}")
    
    def _create_client(self) -> chromadb.ClientAPI:
        """Create Chroma client (sync operation)."""
        try:
            # Try HTTP client first
            client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
            
            # Test connection
            client.heartbeat()
            return client
            
        except Exception as e:
            logger.warning(f"HTTP client failed, falling back to persistent client: {str(e)}")
            
            # Fall back to persistent client
            try:
                return chromadb.PersistentClient(
                    path="./chroma_db",
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    )
                )
            except Exception as fallback_error:
                raise VectorStoreError(f"Both HTTP and persistent clients failed: {str(fallback_error)}")
    
    def _get_or_create_collection(self) -> Collection:
        """Get or create the solutions collection (sync operation)."""
        if not self.client:
            raise VectorStoreError("Chroma client not initialized")
            
        try:
            # Try to get existing collection
            collection = self.client.get_collection(
                name=settings.chroma_collection_name
            )
            logger.info(f"Using existing collection: {settings.chroma_collection_name}")
            return collection
            
        except Exception:
            # Create new collection
            logger.info(f"Creating new collection: {settings.chroma_collection_name}")
            return self.client.create_collection(
                name=settings.chroma_collection_name,
                metadata={
                    "description": "SolarWinds IT Solutions",
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
    
    async def disconnect(self) -> None:
        """Disconnect from Chroma database."""
        try:
            # Chroma client doesn't require explicit disconnection
            self.client = None
            self.collection = None
            self.executor.shutdown(wait=True)
            logger.info("Disconnected from Chroma vector store")
            
        except Exception as e:
            logger.error(f"Error disconnecting from Chroma: {str(e)}")
    
    async def add_solution(
        self, 
        solution: SolutionRecord, 
        embedding: List[float]
    ) -> None:
        """
        Add a solution to the vector store.
        
        Args:
            solution: Solution record to add
            embedding: Vector embedding for the solution
        """
        if not self.collection:
            raise VectorStoreError("Vector store not connected")
        
        try:
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                self.executor,
                self._add_solution_sync,
                solution,
                embedding
            )
            
            logger.debug(f"Added solution to vector store: {solution.title}")
            
        except Exception as e:
            logger.error(f"Error adding solution to vector store: {str(e)}")
            raise VectorStoreError(f"Failed to add solution: {str(e)}")
    
    def _add_solution_sync(
        self, 
        solution: SolutionRecord, 
        embedding: List[float]
    ) -> None:
        """Add solution synchronously."""
        if not self.collection:
            raise VectorStoreError("Collection not available")
        
        # Prepare metadata
        metadata = {
            "title": solution.title,
            "category": solution.category,
            "updated_at": solution.updated_at.isoformat(),
            "tags": ",".join(solution.tags) if solution.tags else "",
            "url": solution.url or "",
            "content_length": len(solution.content),
        }
        
        # Add to collection
        self.collection.add(
            embeddings=[embedding],
            documents=[solution.content],
            metadatas=[metadata],
            ids=[solution.id]
        )
    
    async def add_solutions_batch(
        self, 
        solutions: List[SolutionRecord], 
        embeddings: List[List[float]]
    ) -> None:
        """
        Add multiple solutions to the vector store in batch.
        
        Args:
            solutions: List of solution records
            embeddings: List of corresponding embeddings
        """
        if not self.collection:
            raise VectorStoreError("Vector store not connected")
        
        if len(solutions) != len(embeddings):
            raise VectorStoreError("Solutions and embeddings count mismatch")
        
        try:
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                self.executor,
                self._add_solutions_batch_sync,
                solutions,
                embeddings
            )
            
            logger.info(f"Added {len(solutions)} solutions to vector store in batch")
            
        except Exception as e:
            logger.error(f"Error adding solutions batch to vector store: {str(e)}")
            raise VectorStoreError(f"Failed to add solutions batch: {str(e)}")
    
    def _add_solutions_batch_sync(
        self, 
        solutions: List[SolutionRecord], 
        embeddings: List[List[float]]
    ) -> None:
        """Add solutions batch synchronously."""
        if not self.collection:
            raise VectorStoreError("Collection not available")
        
        # Prepare batch data
        ids = [solution.id for solution in solutions]
        documents = [solution.content for solution in solutions]
        metadatas = []
        
        for solution in solutions:
            metadata = {
                "title": solution.title,
                "category": solution.category,
                "updated_at": solution.updated_at.isoformat(),
                "tags": ",".join(solution.tags) if solution.tags else "",
                "url": solution.url or "",
                "content_length": len(solution.content),
            }
            metadatas.append(metadata)
        
        # Add batch to collection
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    async def search_similar(
        self, 
        query_embedding: List[float], 
        top_k: int = 4,
        category_filter: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[SourceDoc]:
        """
        Search for similar solutions using vector similarity.
        
        Args:
            query_embedding: Query vector embedding
            top_k: Number of results to return
            category_filter: Optional category filter
            min_score: Minimum similarity score threshold
            
        Returns:
            List of source documents with similarity scores
        """
        if not self.collection:
            raise VectorStoreError("Vector store not connected")
        
        try:
            loop = asyncio.get_event_loop()
            
            results = await loop.run_in_executor(
                self.executor,
                self._search_similar_sync,
                query_embedding,
                top_k,
                category_filter
            )
            
            # Convert results to SourceDoc objects
            source_docs = []
            for i, (doc_id, metadata, distance) in enumerate(results):
                # Convert distance to similarity score (Chroma uses L2 distance)
                similarity_score = max(0.0, 1.0 - distance)
                
                if similarity_score >= min_score:
                    source_doc = SourceDoc(
                        id=doc_id,
                        title=metadata.get("title", "Unknown"),
                        score=similarity_score,
                        category=metadata.get("category"),
                        url=metadata.get("url"),
                    )
                    source_docs.append(source_doc)
            
            logger.info(f"Vector search returned {len(source_docs)} results", extra={
                "top_k": top_k,
                "category_filter": category_filter,
                "min_score": min_score,
            })
            
            return source_docs
            
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            raise VectorStoreError(f"Vector search failed: {str(e)}")
    
    def _search_similar_sync(
        self, 
        query_embedding: List[float], 
        top_k: int,
        category_filter: Optional[str] = None
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        """Search similar documents synchronously."""
        if not self.collection:
            raise VectorStoreError("Collection not available")
        
        # Prepare where clause for filtering
        where_clause = None
        if category_filter:
            where_clause = {"category": category_filter}
        
        # Query the collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )
        
        # Extract results
        result_list = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                result_list.append((doc_id, metadata, distance))
        
        return result_list
    
    async def get_solution_by_id(self, solution_id: str) -> Optional[SolutionRecord]:
        """
        Get a solution by its ID.
        
        Args:
            solution_id: Solution ID to retrieve
            
        Returns:
            Solution record if found, None otherwise
        """
        if not self.collection:
            raise VectorStoreError("Vector store not connected")
        
        try:
            loop = asyncio.get_event_loop()
            
            result = await loop.run_in_executor(
                self.executor,
                self._get_solution_by_id_sync,
                solution_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving solution by ID: {str(e)}")
            raise VectorStoreError(f"Failed to retrieve solution: {str(e)}")
    
    def _get_solution_by_id_sync(self, solution_id: str) -> Optional[SolutionRecord]:
        """Get solution by ID synchronously."""
        if not self.collection:
            raise VectorStoreError("Collection not available")
        
        try:
            results = self.collection.get(
                ids=[solution_id],
                include=["documents", "metadatas"]
            )
            
            if results["ids"] and results["ids"][0] == solution_id:
                metadata = results["metadatas"][0]
                document = results["documents"][0]
                
                # Parse tags
                tags = []
                if metadata.get("tags"):
                    tags = [tag.strip() for tag in metadata["tags"].split(",") if tag.strip()]
                
                # Parse updated_at
                updated_at = datetime.utcnow()
                if metadata.get("updated_at"):
                    try:
                        updated_at = datetime.fromisoformat(metadata["updated_at"])
                    except ValueError:
                        pass
                
                return SolutionRecord(
                    id=solution_id,
                    title=metadata.get("title", "Unknown"),
                    category=metadata.get("category", "General"),
                    content=document,
                    updated_at=updated_at,
                    tags=tags,
                    url=metadata.get("url"),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in get_solution_by_id_sync: {str(e)}")
            return None
    
    async def update_solution(
        self, 
        solution: SolutionRecord, 
        embedding: List[float]
    ) -> None:
        """
        Update an existing solution in the vector store.
        
        Args:
            solution: Updated solution record
            embedding: New vector embedding
        """
        if not self.collection:
            raise VectorStoreError("Vector store not connected")
        
        try:
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                self.executor,
                self._update_solution_sync,
                solution,
                embedding
            )
            
            logger.debug(f"Updated solution in vector store: {solution.title}")
            
        except Exception as e:
            logger.error(f"Error updating solution in vector store: {str(e)}")
            raise VectorStoreError(f"Failed to update solution: {str(e)}")
    
    def _update_solution_sync(
        self, 
        solution: SolutionRecord, 
        embedding: List[float]
    ) -> None:
        """Update solution synchronously."""
        if not self.collection:
            raise VectorStoreError("Collection not available")
        
        # Prepare metadata
        metadata = {
            "title": solution.title,
            "category": solution.category,
            "updated_at": solution.updated_at.isoformat(),
            "tags": ",".join(solution.tags) if solution.tags else "",
            "url": solution.url or "",
            "content_length": len(solution.content),
        }
        
        # Update in collection
        self.collection.update(
            ids=[solution.id],
            embeddings=[embedding],
            documents=[solution.content],
            metadatas=[metadata]
        )
    
    async def delete_solution(self, solution_id: str) -> None:
        """
        Delete a solution from the vector store.
        
        Args:
            solution_id: ID of solution to delete
        """
        if not self.collection:
            raise VectorStoreError("Vector store not connected")
        
        try:
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                self.executor,
                self._delete_solution_sync,
                solution_id
            )
            
            logger.debug(f"Deleted solution from vector store: {solution_id}")
            
        except Exception as e:
            logger.error(f"Error deleting solution from vector store: {str(e)}")
            raise VectorStoreError(f"Failed to delete solution: {str(e)}")
    
    def _delete_solution_sync(self, solution_id: str) -> None:
        """Delete solution synchronously."""
        if not self.collection:
            raise VectorStoreError("Collection not available")
        
        self.collection.delete(ids=[solution_id])
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store collection.
        
        Returns:
            Dictionary with collection statistics
        """
        if not self.collection:
            return {"error": "Vector store not connected"}
        
        try:
            loop = asyncio.get_event_loop()
            
            stats = await loop.run_in_executor(
                self.executor,
                self._get_collection_stats_sync
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {"error": str(e)}
    
    def _get_collection_stats_sync(self) -> Dict[str, Any]:
        """Get collection statistics synchronously."""
        if not self.collection:
            return {"error": "Collection not available"}
        
        try:
            count = self.collection.count()
            
            # Get sample of documents to analyze categories
            sample_results = self.collection.get(
                limit=min(100, count) if count > 0 else 0,
                include=["metadatas"]
            )
            
            categories = {}
            if sample_results["metadatas"]:
                for metadata in sample_results["metadatas"]:
                    category = metadata.get("category", "Unknown")
                    categories[category] = categories.get(category, 0) + 1
            
            return {
                "total_documents": count,
                "collection_name": settings.chroma_collection_name,
                "categories": categories,
                "sample_size": len(sample_results["metadatas"]) if sample_results["metadatas"] else 0,
            }
            
        except Exception as e:
            return {"error": str(e)}


# Global service instance
vector_store_service = VectorStoreService()