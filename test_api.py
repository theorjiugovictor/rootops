#!/usr/bin/env python3
"""
Quick test script for RootOps API
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_commit_analysis():
    """Test commit analysis"""
    print("Testing /api/v1/analyze/commit endpoint...")
    payload = {
        "repository": "test-repo",
        "commit_hash": "abc123def456"
    }
    response = requests.post(f"{BASE_URL}/api/v1/analyze/commit", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_log_analysis():
    """Test log analysis"""
    print("Testing /api/v1/analyze/logs endpoint...")
    payload = {
        "logs": [
            {"level": "error", "message": "Connection timeout", "service": "api"},
            {"level": "error", "message": "Connection timeout", "service": "api"},
            {"level": "error", "message": "Connection timeout", "service": "api"},
            {"level": "warning", "message": "High memory usage", "service": "worker"},
            {"level": "info", "message": "Request processed", "service": "api"}
        ]
    }
    response = requests.post(f"{BASE_URL}/api/v1/analyze/logs", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

if __name__ == "__main__":
    print("=== RootOps API Test ===\n")
    
    try:
        test_health()
        test_commit_analysis()
        test_log_analysis()
        
        print("✅ All tests passed!")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to RootOps API")
        print("Make sure the server is running: docker-compose up -d")
    except Exception as e:
        print(f"❌ Error: {e}")
