#!/usr/bin/env python3
"""End-to-end system test for SolarWinds IT Solutions Chatbot."""

import asyncio
import sys
import requests
import time
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

API_BASE_URL = "http://localhost:8000"
STREAMLIT_URL = "http://localhost:8501"


def test_api_endpoints():
    """Test FastAPI endpoints."""
    print("Testing FastAPI endpoints...")
    
    # Test root endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=10)
        if response.status_code == 200:
            print("  [OK] Root endpoint accessible")
        else:
            print(f"  [FAIL] Root endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Root endpoint failed: {e}")
        return False
    
    # Test health endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  [OK] Health endpoint: {data.get('status', 'unknown')}")
            
            # Check components
            components = data.get('components', {})
            for component, info in components.items():
                status = info.get('status', 'unknown')
                print(f"    - {component}: {status}")
        else:
            print(f"  [FAIL] Health endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Health endpoint failed: {e}")
        return False
    
    # Test chat endpoint
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/chat",
            json={"query": "How do I reset a password?"},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            answer_length = len(data.get('answer', ''))
            sources_count = len(data.get('sources', []))
            response_time = data.get('response_time_ms', 0)
            print(f"  [OK] Chat endpoint: {answer_length} chars, {sources_count} sources, {response_time}ms")
        else:
            print(f"  [FAIL] Chat endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Chat endpoint failed: {e}")
        return False
    
    # Test solutions search
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/solutions/search",
            params={"q": "printer", "limit": 5},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print(f"  [OK] Solutions search: {len(data)} results")
        else:
            print(f"  [FAIL] Solutions search returned {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Solutions search failed: {e}")
        return False
    
    # Test stats endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/solutions/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            total_docs = data.get('total_documents', 0)
            print(f"  [OK] Solutions stats: {total_docs} documents indexed")
        else:
            print(f"  [FAIL] Solutions stats returned {response.status_code}")
    except Exception as e:
        print(f"  [FAIL] Solutions stats failed: {e}")
    
    return True


def test_streamlit_frontend():
    """Test Streamlit frontend availability."""
    print("\nTesting Streamlit frontend...")
    
    try:
        # Test Streamlit health check
        response = requests.get(f"{STREAMLIT_URL}/_stcore/health", timeout=10)
        if response.status_code == 200:
            print("  [OK] Streamlit health check passed")
        else:
            print(f"  [WARN] Streamlit health check returned {response.status_code}")
    except Exception as e:
        print(f"  [WARN] Streamlit health check failed: {e}")
    
    try:
        # Test main Streamlit page
        response = requests.get(STREAMLIT_URL, timeout=10)
        if response.status_code == 200:
            print("  [OK] Streamlit frontend accessible")
            return True
        else:
            print(f"  [FAIL] Streamlit frontend returned {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Streamlit frontend failed: {e}")
        return False


def test_configuration():
    """Test system configuration."""
    print("\nTesting system configuration...")
    
    try:
        from app.core.config import settings
        
        print(f"  [OK] App name: {settings.app_name}")
        print(f"  [OK] Debug mode: {settings.debug}")
        print(f"  [OK] LLM provider: {settings.llm_provider}")
        print(f"  [OK] Embedding provider: {settings.embedding_provider}")
        print(f"  [OK] Mock data enabled: {settings.enable_mock_data}")
        
        # Check required settings
        if settings.llm_provider == "openrouter" and not settings.openrouter_api_key:
            print("  [WARN] OpenRouter API key not configured")
        
        if not settings.enable_mock_data and not settings.solarwinds_api_key:
            print("  [WARN] SolarWinds API key not configured and mock data disabled")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Configuration test failed: {e}")
        return False


def wait_for_service(url, timeout=60):
    """Wait for a service to become available."""
    print(f"Waiting for service at {url}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 404]:  # 404 is OK for root URLs
                print(f"  [OK] Service available at {url}")
                return True
        except Exception:
            pass
        time.sleep(2)
    
    print(f"  [FAIL] Service at {url} not available after {timeout}s")
    return False


def main():
    """Run all system tests."""
    print("SolarWinds IT Solutions Chatbot - End-to-End System Test")
    print("=" * 60)
    
    # Check if services are running
    if not wait_for_service(f"{API_BASE_URL}/", timeout=30):
        print("\n[ERROR] FastAPI service not available. Please start the backend:")
        print("  uv run uvicorn app.main:app --reload")
        return 1
    
    tests = [
        ("Configuration", test_configuration),
        ("API Endpoints", test_api_endpoints),
        ("Streamlit Frontend", test_streamlit_frontend),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"[PASS] {test_name} completed successfully")
            else:
                failed += 1
                print(f"[FAIL] {test_name} failed")
        except Exception as e:
            failed += 1
            print(f"[ERROR] {test_name} crashed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\nAll tests passed! The system is working correctly.")
        print("\nNext steps:")
        print("- Visit http://localhost:8000/docs for API documentation")
        print("- Visit http://localhost:8501 for the Streamlit interface")
        print("- Configure real SolarWinds API credentials for production data")
        print("- Deploy using Docker: docker-compose up -d")
        return 0
    else:
        print("\nSome tests failed. Please check the logs and configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())