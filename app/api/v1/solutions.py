"""Solutions endpoints with SolarWinds integration."""

from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import SolutionRecord, SyncStatus
from app.services.sync_service import sync_service
from app.services.solarwinds import solarwinds_service
from app.services.indexing_service import indexing_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/solutions", response_model=List[SolutionRecord])
async def list_solutions(
    limit: int = 50,
    category: Optional[str] = None
) -> List[SolutionRecord]:
    """
    List solutions endpoint.
    
    Args:
        limit: Maximum number of solutions to return
        category: Optional category filter
    
    Returns:
        List of solution records
    """
    try:
        # Get index stats to see available solutions
        stats = await indexing_service.get_index_stats()
        total_count = stats.get("vector_store", {}).get("total_documents", 0)
        
        if total_count == 0:
            logger.info("No solutions available in index")
            return []
        
        # For now, we'll return a placeholder response since we need a more complex
        # query to list all solutions. The vector store is optimized for semantic search.
        logger.info(f"Solutions list requested - {total_count} available in index")
        
        # TODO: Implement proper listing functionality in vector store
        return []
        
    except Exception as e:
        logger.error(f"Error listing solutions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list solutions: {str(e)}"
        )


@router.get("/solutions/sync-status", response_model=Dict[str, Any])
async def get_sync_status() -> Dict[str, Any]:
    """
    Get sync status endpoint.
    
    Returns:
        Current sync status and statistics
    """
    try:
        sync_status = await sync_service.get_sync_status()
        solarwinds_stats = await solarwinds_service.get_sync_stats()
        
        # Combine sync service status with SolarWinds stats
        combined_status = {
            **sync_status,
            "solarwinds_api": solarwinds_stats,
        }
        
        logger.info("Sync status requested", extra={
            "service_running": sync_status.get("service_running", False),
            "sync_in_progress": sync_status.get("sync_in_progress", False),
        })
        
        return combined_status
        
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}"
        )


@router.post("/solutions/sync")
async def trigger_sync(force: bool = False) -> Dict[str, Any]:
    """
    Trigger manual sync endpoint.
    
    Args:
        force: Force sync even if one is already in progress
        
    Returns:
        Sync operation result
    """
    try:
        logger.info(f"Manual sync triggered with force={force}")
        
        result = await sync_service.trigger_sync(force=force)
        
        logger.info(f"Manual sync completed with status: {result.get('status')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error triggering sync: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger sync: {str(e)}"
        )


@router.get("/solutions/test-connection")
async def test_solarwinds_connection() -> Dict[str, Any]:
    """
    Test SolarWinds API connection.
    
    Returns:
        Connection test result
    """
    try:
        logger.info("Testing SolarWinds API connection")
        
        is_connected = await solarwinds_service.test_connection()
        
        result = {
            "connected": is_connected,
            "timestamp": datetime.utcnow().isoformat(),
            "api_configured": bool(solarwinds_service.client.api_key and solarwinds_service.client.base_url),
        }
        
        if is_connected:
            logger.info("SolarWinds API connection test successful")
        else:
            logger.warning("SolarWinds API connection test failed")
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing SolarWinds connection: {str(e)}")
        return {
            "connected": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/solutions/search")
async def search_solutions(
    q: str,
    limit: int = 10,
    category: Optional[str] = None,
    min_score: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Search solutions using semantic similarity.
    
    Args:
        q: Search query
        limit: Maximum number of results
        category: Optional category filter
        min_score: Minimum similarity score
        
    Returns:
        List of matching solutions with scores
    """
    try:
        if not q.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query parameter 'q' is required"
            )
        
        logger.info(f"Solution search requested: '{q[:100]}'")
        
        results = await indexing_service.search_solutions(
            query=q,
            top_k=limit,
            category_filter=category,
            min_score=min_score
        )
        
        return [result.model_dump() for result in results]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching solutions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Solution search failed: {str(e)}"
        )


@router.get("/solutions/stats")
async def get_index_stats() -> Dict[str, Any]:
    """
    Get statistics about the solution index.
    
    Returns:
        Index statistics and health information
    """
    try:
        stats = await indexing_service.get_index_stats()
        health = await indexing_service.health_check()
        
        return {
            **stats,
            "health": health,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error getting index stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get index stats: {str(e)}"
        )


@router.get("/solutions/{solution_id}")
async def get_solution(solution_id: str) -> Dict[str, Any]:
    """
    Get a specific solution by ID.
    
    Args:
        solution_id: Solution ID
        
    Returns:
        Solution details
    """
    try:
        solution = await indexing_service.get_solution_by_id(solution_id)
        
        if not solution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Solution not found: {solution_id}"
            )
        
        return solution.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting solution: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get solution: {str(e)}"
        )