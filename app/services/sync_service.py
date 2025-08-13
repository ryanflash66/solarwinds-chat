"""Background sync service for SolarWinds solutions with APScheduler and Redis."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.exceptions import SolarWindsAPIError, VectorStoreError
from app.core.logging import get_logger
from app.services.solarwinds import solarwinds_service
from app.services.text_processing import text_processing_service
from app.services.indexing_service import indexing_service
from app.services.mock_data import mock_data_service

logger = get_logger(__name__)


class SyncStateManager:
    """Manages sync state using Redis."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.state_key = "solarwinds:sync_state"
        self.lock_key = "solarwinds:sync_lock"
        self.stats_key = "solarwinds:sync_stats"
        
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                db=settings.redis_db,
                decode_responses=True,
                retry_on_error=[redis.ConnectionError, redis.TimeoutError],
                retry_on_timeout=True,
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.aclose()
            self.redis_client = None
    
    async def get_last_sync_time(self) -> Optional[datetime]:
        """Get the last successful sync timestamp."""
        if not self.redis_client:
            return None
            
        try:
            timestamp_str = await self.redis_client.hget(self.state_key, "last_sync_time")
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            logger.error(f"Error getting last sync time: {str(e)}")
        
        return None
    
    async def set_last_sync_time(self, timestamp: datetime) -> None:
        """Set the last successful sync timestamp."""
        if not self.redis_client:
            return
            
        try:
            await self.redis_client.hset(
                self.state_key,
                "last_sync_time",
                timestamp.isoformat()
            )
        except Exception as e:
            logger.error(f"Error setting last sync time: {str(e)}")
    
    async def acquire_sync_lock(self, timeout_seconds: int = 3600) -> bool:
        """
        Acquire sync lock to prevent concurrent syncs.
        
        Args:
            timeout_seconds: Lock timeout in seconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        if not self.redis_client:
            return True  # Allow sync if Redis unavailable
            
        try:
            result = await self.redis_client.set(
                self.lock_key,
                datetime.utcnow().isoformat(),
                ex=timeout_seconds,
                nx=True
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Error acquiring sync lock: {str(e)}")
            return False
    
    async def release_sync_lock(self) -> None:
        """Release the sync lock."""
        if not self.redis_client:
            return
            
        try:
            await self.redis_client.delete(self.lock_key)
        except Exception as e:
            logger.error(f"Error releasing sync lock: {str(e)}")
    
    async def is_sync_in_progress(self) -> bool:
        """Check if sync is currently in progress."""
        if not self.redis_client:
            return False
            
        try:
            return bool(await self.redis_client.exists(self.lock_key))
        except Exception as e:
            logger.error(f"Error checking sync status: {str(e)}")
            return False
    
    async def update_sync_stats(self, stats: Dict[str, Any]) -> None:
        """Update sync statistics."""
        if not self.redis_client:
            return
            
        try:
            stats_with_timestamp = {
                **stats,
                "last_updated": datetime.utcnow().isoformat()
            }
            await self.redis_client.hset(
                self.stats_key,
                mapping=stats_with_timestamp
            )
        except Exception as e:
            logger.error(f"Error updating sync stats: {str(e)}")
    
    async def get_sync_stats(self) -> Dict[str, Any]:
        """Get sync statistics."""
        if not self.redis_client:
            return {}
            
        try:
            return await self.redis_client.hgetall(self.stats_key)
        except Exception as e:
            logger.error(f"Error getting sync stats: {str(e)}")
            return {}


class SyncService:
    """Background sync service for SolarWinds solutions."""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.state_manager = SyncStateManager()
        self.is_running = False
        
    async def start(self) -> None:
        """Start the sync service."""
        if self.is_running:
            logger.warning("Sync service is already running")
            return
            
        try:
            # Connect to Redis
            await self.state_manager.connect()
            
            # Initialize scheduler
            self.scheduler = AsyncIOScheduler()
            
            # Add periodic sync job
            self.scheduler.add_job(
                self._periodic_sync,
                trigger=CronTrigger(
                    minute=f"*/{settings.sync_interval_minutes}"
                ),
                id="solarwinds_sync",
                name="SolarWinds Periodic Sync",
                max_instances=1,
                coalesce=True,
                misfire_grace_time=300,  # 5 minutes grace time
            )
            
            # Add cleanup job (runs daily at 2 AM)
            self.scheduler.add_job(
                self._cleanup_old_data,
                trigger=CronTrigger(hour=2, minute=0),
                id="cleanup_job",
                name="Cleanup Old Data",
                max_instances=1,
            )
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"Sync service started with {settings.sync_interval_minutes} minute interval")
            
            # Run initial sync if it's been a while
            await self._check_initial_sync()
            
        except Exception as e:
            logger.error(f"Failed to start sync service: {str(e)}")
            raise
    
    async def stop(self) -> None:
        """Stop the sync service."""
        if not self.is_running:
            return
            
        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=True)
                self.scheduler = None
            
            await self.state_manager.disconnect()
            self.is_running = False
            
            logger.info("Sync service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping sync service: {str(e)}")
    
    async def _check_initial_sync(self) -> None:
        """Check if we need to run an initial sync."""
        last_sync = await self.state_manager.get_last_sync_time()
        
        if not last_sync:
            logger.info("No previous sync found, scheduling initial sync")
            asyncio.create_task(self.trigger_sync())
        elif datetime.utcnow() - last_sync > timedelta(hours=1):
            logger.info("Last sync was over an hour ago, scheduling sync")
            asyncio.create_task(self.trigger_sync())
    
    async def _periodic_sync(self) -> None:
        """Periodic sync job."""
        try:
            await self.trigger_sync()
        except Exception as e:
            logger.error(f"Error in periodic sync: {str(e)}")
    
    async def trigger_sync(self, force: bool = False) -> Dict[str, Any]:
        """
        Trigger a sync operation.
        
        Args:
            force: Force sync even if one is in progress
            
        Returns:
            Sync result dictionary
        """
        # Check if sync is already in progress
        if not force and await self.state_manager.is_sync_in_progress():
            return {
                "status": "skipped",
                "reason": "Sync already in progress",
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        # Try to acquire lock
        if not await self.state_manager.acquire_sync_lock():
            return {
                "status": "failed",
                "reason": "Could not acquire sync lock",
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        sync_start_time = datetime.utcnow()
        
        try:
            logger.info("Starting SolarWinds sync")
            
            # Check if we should use mock data
            if mock_data_service.is_mock_mode_enabled():
                logger.info("Using mock data for development (SolarWinds API not configured)")
                return await self._sync_mock_data(sync_start_time)
            
            # Get last sync time for delta sync
            last_sync_time = await self.state_manager.get_last_sync_time()
            
            # Test SolarWinds connection
            if not await solarwinds_service.test_connection():
                raise SolarWindsAPIError("SolarWinds API connection test failed")
            
            # Fetch solutions from SolarWinds
            logger.info("Fetching solutions from SolarWinds API")
            solutions = await solarwinds_service.fetch_all_solutions(
                modified_since=last_sync_time
            )
            
            if not solutions:
                logger.info("No new or updated solutions found")
                await self.state_manager.set_last_sync_time(sync_start_time)
                return {
                    "status": "success",
                    "solutions_processed": 0,
                    "duration_seconds": (datetime.utcnow() - sync_start_time).total_seconds(),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            
            # Convert solutions to SolutionRecord objects
            logger.info(f"Converting {len(solutions)} solutions to records")
            solution_records = []
            
            for solution in solutions:
                try:
                    solution_record = solarwinds_service.parse_solution_to_record(solution)
                    solution_records.append(solution_record)
                except Exception as e:
                    logger.error(f"Error parsing solution: {str(e)}")
            
            if not solution_records:
                logger.warning("No valid solution records to index")
                await self.state_manager.set_last_sync_time(sync_start_time)
                return {
                    "status": "success",
                    "solutions_processed": 0,
                    "duration_seconds": (datetime.utcnow() - sync_start_time).total_seconds(),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            
            # Index solutions in vector database
            logger.info(f"Indexing {len(solution_records)} solutions in vector database")
            indexing_result = await indexing_service.index_solutions_batch(solution_records)
            
            successful_count = indexing_result.get("indexed", 0)
            failed_count = indexing_result.get("failed", 0) + indexing_result.get("skipped", 0)
            
            # Update sync state
            await self.state_manager.set_last_sync_time(sync_start_time)
            
            # Update statistics
            duration = (datetime.utcnow() - sync_start_time).total_seconds()
            stats = {
                "total_solutions": len(solutions),
                "successful_count": successful_count,
                "failed_count": failed_count,
                "last_sync_duration": duration,
                "last_sync_status": "success",
            }
            await self.state_manager.update_sync_stats(stats)
            
            logger.info(f"Sync completed successfully: {successful_count} processed, {failed_count} failed")
            
            return {
                "status": "success",
                "solutions_processed": successful_count,
                "solutions_failed": failed_count,
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            
            # Update error statistics
            duration = (datetime.utcnow() - sync_start_time).total_seconds()
            stats = {
                "last_sync_duration": duration,
                "last_sync_status": "failed",
                "last_error": str(e),
                "last_error_time": datetime.utcnow().isoformat(),
            }
            await self.state_manager.update_sync_stats(stats)
            
            return {
                "status": "failed",
                "error": str(e),
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        finally:
            # Always release the lock
            await self.state_manager.release_sync_lock()
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old data and logs."""
        try:
            logger.info("Running cleanup job")
            
            # TODO: Implement cleanup logic
            # - Remove old vector store entries
            # - Clean up temporary files
            # - Archive old logs
            
            logger.info("Cleanup job completed")
            
        except Exception as e:
            logger.error(f"Error in cleanup job: {str(e)}")
    
    async def _sync_mock_data(self, sync_start_time: datetime) -> Dict[str, Any]:
        """Sync mock data for development."""
        try:
            logger.info("Generating and indexing mock solutions")
            
            # Generate mock solutions
            mock_solutions = mock_data_service.generate_mock_solutions()
            
            if not mock_solutions:
                logger.warning("No mock solutions generated")
                return {
                    "status": "success",
                    "solutions_processed": 0,
                    "duration_seconds": (datetime.utcnow() - sync_start_time).total_seconds(),
                    "timestamp": datetime.utcnow().isoformat(),
                    "mode": "mock",
                }
            
            # Index solutions in vector database
            logger.info(f"Indexing {len(mock_solutions)} mock solutions")
            indexing_result = await indexing_service.index_solutions_batch(mock_solutions)
            
            successful_count = indexing_result.get("indexed", 0)
            failed_count = indexing_result.get("failed", 0) + indexing_result.get("skipped", 0)
            
            # Update sync state
            await self.state_manager.set_last_sync_time(sync_start_time)
            
            # Update statistics
            duration = (datetime.utcnow() - sync_start_time).total_seconds()
            stats = {
                "total_solutions": len(mock_solutions),
                "successful_count": successful_count,
                "failed_count": failed_count,
                "duration_seconds": duration,
                "last_sync_time": sync_start_time.isoformat(),
                "mode": "mock",
            }
            await self.state_manager.update_sync_stats(stats)
            
            logger.info(f"Mock sync completed: {successful_count} indexed, {failed_count} failed")
            
            return {
                "status": "success",
                "solutions_processed": successful_count,
                "failed_count": failed_count,
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat(),
                "mode": "mock",
            }
            
        except Exception as e:
            logger.error(f"Error in mock data sync: {str(e)}")
            raise
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        try:
            last_sync_time = await self.state_manager.get_last_sync_time()
            is_in_progress = await self.state_manager.is_sync_in_progress()
            stats = await self.state_manager.get_sync_stats()
            
            # Calculate next sync time
            next_sync_time = None
            if self.scheduler and self.scheduler.running:
                jobs = self.scheduler.get_jobs()
                sync_job = next((job for job in jobs if job.id == "solarwinds_sync"), None)
                if sync_job:
                    next_sync_time = sync_job.next_run_time
            
            return {
                "service_running": self.is_running,
                "sync_in_progress": is_in_progress,
                "last_sync_time": last_sync_time.isoformat() if last_sync_time else None,
                "next_sync_time": next_sync_time.isoformat() if next_sync_time else None,
                "sync_interval_minutes": settings.sync_interval_minutes,
                "statistics": stats,
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            return {
                "service_running": self.is_running,
                "error": str(e),
            }


# Global service instance
sync_service = SyncService()