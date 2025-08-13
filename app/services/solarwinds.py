"""SolarWinds API client and integration service."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.exceptions import SolarWindsAPIError, RateLimitError
from app.core.logging import get_logger
from app.models.schemas import SolutionRecord

logger = get_logger(__name__)


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
        
    async def acquire(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = time.time()
        
        # Remove old requests outside the window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.window_seconds]
        
        # Check if we're at the limit
        if len(self.requests) >= self.max_requests:
            sleep_time = self.window_seconds - (now - self.requests[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
                return await self.acquire()  # Recursive call after sleeping
        
        # Record this request
        self.requests.append(now)


class SolarWindsClient:
    """Async SolarWinds API client with rate limiting and error handling."""
    
    def __init__(self):
        self.base_url = settings.solarwinds_base_url
        self.api_key = settings.solarwinds_api_key
        self.rate_limiter = RateLimiter(max_requests=settings.solarwinds_rate_limit)
        self.client: Optional[httpx.AsyncClient] = None
        
        if not self.base_url or not self.api_key:
            logger.warning("SolarWinds API configuration missing - client will be disabled")
            
    async def __aenter__(self):
        """Async context manager entry."""
        if self.api_key and self.base_url:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "SolarWinds-Chatbot/1.0.0",
                },
                timeout=httpx.Timeout(30.0),
            )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def _validate_client(self) -> None:
        """Validate that client is properly configured."""
        if not self.client:
            raise SolarWindsAPIError(
                "SolarWinds client not configured - missing API key or base URL",
                details={"configured": False}
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make authenticated request with retry logic."""
        self._validate_client()
        
        await self.rate_limiter.acquire()
        
        try:
            url = urljoin(self.base_url, endpoint.lstrip('/'))
            
            logger.debug(f"Making {method} request to {url}", extra={
                "method": method,
                "endpoint": endpoint,
                "params": params,
            })
            
            response = await self.client.request(
                method=method,
                url=endpoint,
                params=params,
                **kwargs
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited by SolarWinds API, waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)
                raise RateLimitError(f"Rate limited, retry after {retry_after} seconds")
            
            # Raise for HTTP errors
            response.raise_for_status()
            
            logger.info(f"Successful {method} request to {endpoint}", extra={
                "status_code": response.status_code,
                "response_size": len(response.content),
            })
            
            return response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in SolarWinds API request", extra={
                "status_code": e.response.status_code,
                "endpoint": endpoint,
                "error": str(e),
            })
            raise SolarWindsAPIError(
                f"SolarWinds API HTTP error: {e.response.status_code}",
                details={
                    "status_code": e.response.status_code,
                    "endpoint": endpoint,
                    "response_body": e.response.text[:1000],  # Limit response body
                }
            )
        except httpx.RequestError as e:
            logger.error(f"Request error in SolarWinds API", extra={
                "endpoint": endpoint,
                "error": str(e),
            })
            raise SolarWindsAPIError(
                f"SolarWinds API request error: {str(e)}",
                details={"endpoint": endpoint, "error_type": type(e).__name__}
            )
    
    async def get_solutions(
        self, 
        modified_since: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get solutions from SolarWinds API.
        
        Args:
            modified_since: Only return solutions modified after this date
            limit: Maximum number of solutions to return
            offset: Pagination offset
            
        Returns:
            Dict containing solutions and pagination info
        """
        params = {
            "limit": limit,
            "offset": offset,
        }
        
        if modified_since:
            params["modifiedSince"] = modified_since.isoformat()
        
        response = await self._make_request("GET", "/solutions", params=params)
        return response.json()
    
    async def get_solution_by_id(self, solution_id: str) -> Dict[str, Any]:
        """
        Get a specific solution by ID.
        
        Args:
            solution_id: Unique solution identifier
            
        Returns:
            Solution data
        """
        response = await self._make_request("GET", f"/solutions/{solution_id}")
        return response.json()
    
    async def search_solutions(
        self, 
        query: str, 
        categories: Optional[List[str]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search solutions in SolarWinds API.
        
        Args:
            query: Search query string
            categories: Optional list of categories to filter by
            limit: Maximum number of results
            
        Returns:
            Search results
        """
        params = {
            "q": query,
            "limit": limit,
        }
        
        if categories:
            params["categories"] = ",".join(categories)
        
        response = await self._make_request("GET", "/solutions/search", params=params)
        return response.json()


class SolarWindsService:
    """High-level SolarWinds integration service."""
    
    def __init__(self):
        self.client = SolarWindsClient()
        self.last_sync_time: Optional[datetime] = None
        
    async def fetch_all_solutions(
        self, 
        modified_since: Optional[datetime] = None,
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch all solutions from SolarWinds API with pagination.
        
        Args:
            modified_since: Only fetch solutions modified after this date
            batch_size: Number of solutions to fetch per request
            
        Returns:
            List of all solution records
        """
        all_solutions = []
        offset = 0
        
        logger.info("Starting to fetch solutions from SolarWinds", extra={
            "modified_since": modified_since.isoformat() if modified_since else None,
            "batch_size": batch_size,
        })
        
        async with self.client:
            while True:
                try:
                    batch = await self.client.get_solutions(
                        modified_since=modified_since,
                        limit=batch_size,
                        offset=offset
                    )
                    
                    solutions = batch.get("solutions", [])
                    if not solutions:
                        break
                        
                    all_solutions.extend(solutions)
                    
                    logger.info(f"Fetched batch of {len(solutions)} solutions", extra={
                        "offset": offset,
                        "total_so_far": len(all_solutions),
                    })
                    
                    # Check if we have more pages
                    total_count = batch.get("totalCount")
                    if total_count and len(all_solutions) >= total_count:
                        break
                        
                    offset += batch_size
                    
                    # Add small delay between requests to be respectful
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error fetching solutions batch at offset {offset}", extra={
                        "error": str(e),
                        "offset": offset,
                    })
                    raise
        
        logger.info(f"Successfully fetched {len(all_solutions)} solutions from SolarWinds")
        return all_solutions
    
    def parse_solution_to_record(self, solution_data: Dict[str, Any]) -> SolutionRecord:
        """
        Parse SolarWinds solution data into our SolutionRecord model.
        
        Args:
            solution_data: Raw solution data from SolarWinds API
            
        Returns:
            Parsed SolutionRecord
        """
        # Handle different possible field names and structures
        solution_id = solution_data.get("id") or solution_data.get("solutionId")
        title = solution_data.get("title") or solution_data.get("name", "Untitled Solution")
        category = solution_data.get("category") or solution_data.get("type", "General")
        content = solution_data.get("content") or solution_data.get("body") or solution_data.get("description", "")
        
        # Parse timestamp
        updated_str = solution_data.get("updatedAt") or solution_data.get("lastModified")
        if updated_str:
            try:
                updated_at = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = datetime.utcnow()
        else:
            updated_at = datetime.utcnow()
        
        # Extract tags
        tags = solution_data.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Build URL if available
        url = solution_data.get("url") or solution_data.get("link")
        if not url and solution_id:
            url = f"{settings.solarwinds_base_url}/solutions/{solution_id}"
        
        return SolutionRecord(
            id=str(solution_id),
            title=title,
            category=category,
            content=content,
            updated_at=updated_at,
            tags=tags or [],
            url=url,
        )
    
    async def test_connection(self) -> bool:
        """
        Test the connection to SolarWinds API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        if not settings.solarwinds_api_key or not settings.solarwinds_base_url:
            logger.warning("SolarWinds API not configured")
            return False
            
        try:
            async with self.client:
                # Try to fetch a small batch of solutions to test the connection
                await self.client.get_solutions(limit=1)
                logger.info("SolarWinds API connection test successful")
                return True
        except Exception as e:
            logger.error(f"SolarWinds API connection test failed: {str(e)}")
            return False
    
    async def get_sync_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the SolarWinds integration.
        
        Returns:
            Dictionary with sync statistics
        """
        return {
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "api_configured": bool(settings.solarwinds_api_key and settings.solarwinds_base_url),
            "rate_limit": settings.solarwinds_rate_limit,
            "base_url": settings.solarwinds_base_url,
        }


# Global service instance
solarwinds_service = SolarWindsService()