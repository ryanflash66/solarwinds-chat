"""Solution indexing service that integrates embedding and vector store services."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.core.exceptions import (
    VectorStoreError,
    EmbeddingError,
    IndexingServiceError,
)
from app.core.logging import get_logger
from app.models.schemas import SolutionRecord, SourceDoc
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store_service
from app.services.text_processing import text_processing_service

logger = get_logger(__name__)


class IndexingService:
    """Service for indexing solutions into the vector store with embeddings."""
    
    def __init__(self):
        self._initialized = False
        self._last_error: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize the indexing service and its dependencies."""
        if self._initialized:
            return

        try:
            logger.info("Initializing indexing service")

            # Initialize embedding service
            await embedding_service.initialize()

            # Initialize vector store
            await vector_store_service.connect()

            self._initialized = True
            self._last_error = None
            logger.info("Indexing service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize indexing service: {str(e)}")
            self._initialized = False
            self._last_error = str(e)

    async def cleanup(self) -> None:
        """Cleanup the indexing service."""
        try:
            await embedding_service.cleanup()
            await vector_store_service.disconnect()
            self._initialized = False
            self._last_error = None
            logger.info("Indexing service cleaned up")
        except Exception as e:
            logger.error(f"Error during indexing service cleanup: {str(e)}")
    
    async def index_solution(self, solution: SolutionRecord) -> bool:
        """
        Index a single solution into the vector store.
        
        Args:
            solution: Solution record to index
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Process the solution content
            processed_content = await text_processing_service.process_solution_content(
                solution.content, 
                solution.title
            )
            
            # Validate content quality
            validation = await text_processing_service.validate_content(processed_content)
            if not validation["is_valid"]:
                logger.warning(f"Solution content failed validation: {solution.title}", extra={
                    "issues": validation["issues"],
                    "solution_id": solution.id,
                })
                return False
            
            # Create text for embedding (combine title and content)
            embedding_text = f"{solution.title}\n\n{processed_content}"
            
            # Generate embedding
            embedding = await embedding_service.get_embedding(embedding_text)
            
            # Update solution with processed content
            enhanced_solution = SolutionRecord(
                id=solution.id,
                title=solution.title,
                category=solution.category,
                content=processed_content,
                updated_at=solution.updated_at,
                tags=solution.tags,
                url=solution.url,
            )
            
            # Store in vector database
            await vector_store_service.add_solution(enhanced_solution, embedding)
            
            logger.info(f"Successfully indexed solution: {solution.title}", extra={
                "solution_id": solution.id,
                "content_length": len(processed_content),
                "embedding_dimension": len(embedding),
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error indexing solution '{solution.title}': {str(e)}", extra={
                "solution_id": solution.id,
                "error_type": type(e).__name__,
            })
            return False
    
    async def index_solutions_batch(
        self, 
        solutions: List[SolutionRecord],
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Index multiple solutions in batch.
        
        Args:
            solutions: List of solutions to index
            batch_size: Number of solutions to process concurrently
            
        Returns:
            Dictionary with indexing results
        """
        if not self._initialized:
            await self.initialize()
        
        if not solutions:
            return {"indexed": 0, "failed": 0, "skipped": 0}
        
        start_time = datetime.utcnow()
        indexed_count = 0
        failed_count = 0
        skipped_count = 0
        
        logger.info(f"Starting batch indexing of {len(solutions)} solutions")
        
        try:
            # Process solutions with text processing first
            processed_solutions = await text_processing_service.batch_process_solutions(
                [sol.model_dump() for sol in solutions],
                batch_size=batch_size
            )
            
            # Filter valid solutions and prepare for embedding
            valid_solutions = []
            embedding_texts = []
            
            for processed_sol in processed_solutions:
                validation = processed_sol.get("content_validation", {})
                if validation.get("is_valid", True):
                    # Create solution record
                    solution = SolutionRecord(
                        id=processed_sol["id"],
                        title=processed_sol["title"],
                        category=processed_sol["category"],
                        content=processed_sol["processed_content"],
                        updated_at=datetime.fromisoformat(processed_sol["updated_at"]) if isinstance(processed_sol["updated_at"], str) else processed_sol["updated_at"],
                        tags=processed_sol.get("tags", []),
                        url=processed_sol.get("url"),
                    )
                    valid_solutions.append(solution)
                    
                    # Prepare text for embedding
                    embedding_text = f"{solution.title}\n\n{solution.content}"
                    embedding_texts.append(embedding_text)
                else:
                    skipped_count += 1
                    logger.debug(f"Skipped invalid solution: {processed_sol.get('title', 'Unknown')}")
            
            if not valid_solutions:
                logger.warning("No valid solutions to index")
                return {"indexed": 0, "failed": 0, "skipped": skipped_count}
            
            # Generate embeddings in batch
            logger.info(f"Generating embeddings for {len(valid_solutions)} solutions")
            embeddings = await embedding_service.get_embeddings_batch(
                embedding_texts,
                batch_size=min(batch_size, 20)  # Limit embedding batch size
            )
            
            # Index solutions in vector store batch
            await vector_store_service.add_solutions_batch(valid_solutions, embeddings)
            indexed_count = len(valid_solutions)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Batch indexing completed", extra={
                "total_solutions": len(solutions),
                "indexed": indexed_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "duration_seconds": duration,
            })
            
            return {
                "indexed": indexed_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "duration_seconds": duration,
            }
            
        except Exception as e:
            logger.error(f"Error in batch indexing: {str(e)}")
            return {
                "indexed": indexed_count,
                "failed": len(solutions) - indexed_count - skipped_count,
                "skipped": skipped_count,
                "error": str(e),
            }
    
    async def update_solution_index(self, solution: SolutionRecord) -> bool:
        """
        Update an existing solution in the index.
        
        Args:
            solution: Updated solution record
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Process the solution content
            processed_content = await text_processing_service.process_solution_content(
                solution.content, 
                solution.title
            )
            
            # Validate content quality
            validation = await text_processing_service.validate_content(processed_content)
            if not validation["is_valid"]:
                logger.warning(f"Updated solution content failed validation: {solution.title}")
                return False
            
            # Create text for embedding
            embedding_text = f"{solution.title}\n\n{processed_content}"
            
            # Generate new embedding
            embedding = await embedding_service.get_embedding(embedding_text)
            
            # Update solution with processed content
            enhanced_solution = SolutionRecord(
                id=solution.id,
                title=solution.title,
                category=solution.category,
                content=processed_content,
                updated_at=solution.updated_at,
                tags=solution.tags,
                url=solution.url,
            )
            
            # Update in vector database
            await vector_store_service.update_solution(enhanced_solution, embedding)
            
            logger.info(f"Successfully updated solution index: {solution.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating solution index '{solution.title}': {str(e)}")
            return False
    
    async def remove_solution_from_index(self, solution_id: str) -> bool:
        """
        Remove a solution from the index.
        
        Args:
            solution_id: ID of solution to remove
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            await vector_store_service.delete_solution(solution_id)
            logger.info(f"Successfully removed solution from index: {solution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing solution from index '{solution_id}': {str(e)}")
            return False
    
    async def search_solutions(
        self, 
        query: str, 
        top_k: int = 4,
        category_filter: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[SourceDoc]:
        """
        Search for solutions using semantic similarity.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            category_filter: Optional category filter
            min_score: Minimum similarity score threshold
            
        Returns:
            List of source documents with similarity scores
        """
        if not query.strip():
            return []

        await self.initialize()
        if not self._initialized:
            error_message = self._last_error or "Indexing service not initialized"
            logger.error(
                "Indexing service unavailable for search",
                extra={"error": error_message},
            )
            raise IndexingServiceError(
                "Indexing service unavailable",
                details={
                    "operation": "search_solutions",
                    "error": error_message,
                },
            )

        try:
            query_text = query.strip()
            query_embedding = await embedding_service.get_embedding(query_text)

            results = await vector_store_service.search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                category_filter=category_filter,
                min_score=min_score
            )

            truncated_query = (
                f"{query_text[:100]}..." if len(query_text) > 100 else query_text
            )
            logger.info("Search completed", extra={
                "query": truncated_query,
                "results_count": len(results),
                "top_k": top_k,
                "category_filter": category_filter,
            })

            return results

        except (EmbeddingError, VectorStoreError) as exc:
            self._last_error = str(exc)
            logger.exception(
                "Dependency error during search_solutions",
                extra={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "query": query,
                },
            )
            raise
        except Exception as exc:
            self._last_error = str(exc)
            logger.exception(
                "Unexpected error during search_solutions",
                extra={
                    "query": query,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise IndexingServiceError(
                "Failed to search solutions",
                details={
                    "operation": "search_solutions",
                    "error": str(exc),
                },
            ) from exc
    
    async def get_solution_by_id(self, solution_id: str) -> Optional[SolutionRecord]:
        """
        Get a solution by its ID.
        
        Args:
            solution_id: Solution ID
            
        Returns:
            Solution record if found, None otherwise
        """
        await self.initialize()
        if not self._initialized:
            error_message = self._last_error or "Indexing service not initialized"
            logger.error(
                "Indexing service unavailable when fetching solution by ID",
                extra={"solution_id": solution_id, "error": error_message},
            )
            raise IndexingServiceError(
                "Indexing service unavailable",
                details={
                    "operation": "get_solution_by_id",
                    "solution_id": solution_id,
                    "error": error_message,
                },
            )

        try:
            return await vector_store_service.get_solution_by_id(solution_id)
        except VectorStoreError as exc:
            self._last_error = str(exc)
            logger.exception(
                "Vector store error retrieving solution by ID",
                extra={"solution_id": solution_id},
            )
            raise
        except Exception as exc:
            self._last_error = str(exc)
            logger.exception(
                "Unexpected error retrieving solution by ID",
                extra={
                    "solution_id": solution_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise IndexingServiceError(
                "Failed to retrieve solution",
                details={
                    "operation": "get_solution_by_id",
                    "solution_id": solution_id,
                    "error": str(exc),
                },
            ) from exc
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the solution index.
        
        Returns:
            Dictionary with index statistics
        """
        try:
            if not self._initialized:
                return {
                    "initialized": False,
                    "error": self._last_error or "Service not initialized",
                }

            vector_stats = await vector_store_service.get_collection_stats()
            embedding_info = await embedding_service.get_service_info()

            return {
                "initialized": True,
                "vector_store": vector_stats,
                "embedding_service": embedding_info,
            }

        except Exception as exc:
            self._last_error = str(exc)
            logger.exception(
                "Error getting index stats",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return {
                "initialized": self._initialized,
                "error": str(exc),
                "last_error": self._last_error,
            }
    
    async def rebuild_index(self, solutions: List[SolutionRecord]) -> Dict[str, Any]:
        """
        Rebuild the entire index with provided solutions.
        
        Args:
            solutions: List of all solutions to index
            
        Returns:
            Dictionary with rebuild results
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info(f"Starting index rebuild with {len(solutions)} solutions")
        
        try:
            # Clear existing index (if needed)
            # Note: Chroma doesn't have a clear method, so we'll just add/update
            
            # Index all solutions in batch
            result = await self.index_solutions_batch(solutions)
            
            logger.info(f"Index rebuild completed", extra=result)
            return result
            
        except Exception as e:
            logger.error(f"Error rebuilding index: {str(e)}")
            return {
                "indexed": 0,
                "failed": len(solutions),
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the indexing service.
        
        Returns:
            Dictionary with health status
        """
        if not self._initialized:
            return {
                "healthy": False,
                "error": self._last_error or "Service not initialized",
                "timestamp": datetime.utcnow().isoformat(),
            }

        return {
            "healthy": True,
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global service instance
indexing_service = IndexingService()