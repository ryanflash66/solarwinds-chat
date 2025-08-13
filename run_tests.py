#!/usr/bin/env python3
"""Simple test runner to check if our basic functionality works."""

import sys
import traceback
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that we can import our main modules."""
    print("Testing module imports...")
    
    try:
        from app.core.config import settings
        print("  [OK] Config module imported successfully")
        
        from app.models.schemas import ChatRequest
        print("  [OK] Schemas module imported successfully")
        
        from app.main import app
        print("  [OK] FastAPI app imported successfully")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Import failed: {e}")
        traceback.print_exc()
        return False

def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("\nTesting basic functionality...")
    
    try:
        from app.core.config import settings
        from app.models.schemas import ChatRequest, SourceDoc
        
        # Test settings
        assert settings.app_name == "SolarWinds IT Solutions Chatbot"
        assert settings.api_v1_prefix == "/api/v1"
        print("  [OK] Settings validation passed")
        
        # Test schemas
        request = ChatRequest(query="Test query")
        assert request.query == "Test query"
        print("  [OK] ChatRequest schema validation passed")
        
        doc = SourceDoc(id="test", title="Test Doc", score=0.5)
        assert doc.id == "test"
        assert doc.score == 0.5
        print("  [OK] SourceDoc schema validation passed")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Basic functionality test failed: {e}")
        traceback.print_exc()
        return False

def test_fastapi_app():
    """Test that FastAPI app can be created."""
    print("\nTesting FastAPI app creation...")
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        # Create test client (this will trigger app startup events)
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("  [OK] FastAPI app creation and root endpoint test passed")
        
        return True
    except Exception as e:
        print(f"  [FAIL] FastAPI app test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Starting basic functionality tests...\n")
    
    tests = [
        test_imports,
        test_basic_functionality,
        test_fastapi_app,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[CRASH] Test {test.__name__} crashed: {e}")
            failed += 1
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())