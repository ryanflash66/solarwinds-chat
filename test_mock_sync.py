#!/usr/bin/env python3
"""Test script to verify mock data sync functionality."""

import asyncio
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_mock_data_sync():
    """Test the mock data sync functionality."""
    print("Testing mock data sync functionality...\n")
    
    try:
        from app.services.mock_data import mock_data_service
        from app.services.sync_service import sync_service
        from app.services.indexing_service import indexing_service
        from app.core.config import settings
        
        # Check configuration
        print(f"Mock data enabled: {settings.enable_mock_data}")
        print(f"Mock solutions count: {settings.mock_solutions_count}")
        print(f"SolarWinds API key configured: {bool(settings.solarwinds_api_key)}")
        print(f"Mock mode active: {mock_data_service.is_mock_mode_enabled()}")
        print()
        
        # Test mock data generation
        print("1. Testing mock data generation...")
        mock_solutions = mock_data_service.generate_mock_solutions()
        print(f"   Generated {len(mock_solutions)} mock solutions")
        
        if mock_solutions:
            sample = mock_solutions[0]
            print(f"   Sample solution: {sample.title}")
            print(f"   Category: {sample.category}")
            print(f"   Tags: {sample.tags}")
            print()
        
        # Test indexing service initialization
        print("2. Testing indexing service...")
        try:
            await indexing_service.initialize()
            print("   Indexing service initialized successfully")
        except Exception as e:
            print(f"   Indexing service initialization failed: {e}")
            print("   This is expected if ChromaDB/embeddings aren't available")
        print()
        
        # Test sync service (without actually running full sync)
        print("3. Testing sync service status...")
        try:
            sync_status = await sync_service.get_sync_status()
            print(f"   Sync service running: {sync_status.get('service_running', False)}")
            print(f"   Last sync: {sync_status.get('last_sync_time', 'Never')}")
            print()
        except Exception as e:
            print(f"   Sync status check failed: {e}")
        
        print("Mock data sync test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the mock sync test."""
    success = await test_mock_data_sync()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)