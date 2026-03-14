#!/usr/bin/env python3
"""
Test script to verify authentication modes work correctly.

This script tests the three authentication modes:
- FREE Mode: Public access, no login required
- BASIC Mode: Username/password required
- JWT Mode: Token-based authentication
"""

import os
import sys
import asyncio
import httpx
from typing import Dict, Any

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from config.settings import Settings


class AuthModeTester:
    """Test different authentication modes."""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_free_mode(self):
        """Test FREE mode - should allow unauthenticated access."""
        print("Testing FREE Mode...")
        
        # Test health check (should always work)
        response = await self.client.get(f"{self.base_url}/api/health")
        print(f"Health check: {response.status_code}")
        
        # Test session info (should create guest session)
        response = await self.client.get(f"{self.base_url}/api/v1/auth/session")
        print(f"Session info: {response.status_code}")
        if response.status_code == 200:
            session_data = response.json()
            print(f"Session created: {session_data}")
        
        # Test scan creation (should work in FREE mode)
        scan_data = {
            "name": "Test Scan",
            "description": "Test scan for FREE mode",
            "scan_type": "repository",
            "target_url": "https://github.com/example/repo",
            "target_type": "git"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/scans/",
            json=scan_data
        )
        print(f"Scan creation: {response.status_code}")
        if response.status_code == 201:
            scan_data = response.json()
            print(f"Scan created: {scan_data}")
        
        print("FREE Mode test completed\n")
    
    async def test_basic_mode(self):
        """Test BASIC mode - should require authentication."""
        print("Testing BASIC Mode...")
        
        # Test session info (should create guest session)
        response = await self.client.get(f"{self.base_url}/api/v1/auth/session")
        print(f"Session info: {response.status_code}")
        
        # Test scan creation (should fail without auth in BASIC mode)
        scan_data = {
            "name": "Test Scan",
            "description": "Test scan for BASIC mode",
            "scan_type": "repository",
            "target_url": "https://github.com/example/repo",
            "target_type": "git"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/scans/",
            json=scan_data
        )
        print(f"Scan creation (no auth): {response.status_code}")
        
        # Test login
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/auth/login",
            json=login_data
        )
        print(f"Login: {response.status_code}")
        if response.status_code == 200:
            login_result = response.json()
            token = login_result.get("access_token")
            print(f"Login successful, token: {token[:20]}...")
            
            # Test scan creation with auth
            headers = {"Authorization": f"Bearer {token}"}
            response = await self.client.post(
                f"{self.base_url}/api/v1/scans/",
                json=scan_data,
                headers=headers
            )
            print(f"Scan creation (with auth): {response.status_code}")
        
        print("BASIC Mode test completed\n")
    
    async def test_jwt_mode(self):
        """Test JWT mode - should require token authentication."""
        print("Testing JWT Mode...")
        
        # Test session info (should create guest session)
        response = await self.client.get(f"{self.base_url}/api/v1/auth/session")
        print(f"Session info: {response.status_code}")
        
        # Test scan creation (should fail without token in JWT mode)
        scan_data = {
            "name": "Test Scan",
            "description": "Test scan for JWT mode",
            "scan_type": "repository",
            "target_url": "https://github.com/example/repo",
            "target_type": "git"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/scans/",
            json=scan_data
        )
        print(f"Scan creation (no token): {response.status_code}")
        
        # Test login to get token
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/auth/login",
            json=login_data
        )
        print(f"Login: {response.status_code}")
        if response.status_code == 200:
            login_result = response.json()
            token = login_result.get("access_token")
            print(f"Login successful, token: {token[:20]}...")
            
            # Test scan creation with token
            headers = {"Authorization": f"Bearer {token}"}
            response = await self.client.post(
                f"{self.base_url}/api/v1/scans/",
                json=scan_data,
                headers=headers
            )
            print(f"Scan creation (with token): {response.status_code}")
        
        print("JWT Mode test completed\n")
    
    async def test_configuration(self):
        """Test configuration endpoints."""
        print("Testing Configuration...")
        
        # Test API info
        response = await self.client.get(f"{self.base_url}/api/info")
        print(f"API Info: {response.status_code}")
        if response.status_code == 200:
            info = response.json()
            print(f"API Name: {info.get('name')}")
            print(f"API Version: {info.get('version')}")
        
        print("Configuration test completed\n")
    
    async def run_all_tests(self):
        """Run all authentication mode tests."""
        print("Starting Authentication Mode Tests")
        print("=" * 50)
        
        try:
            await self.test_configuration()
            await self.test_free_mode()
            await self.test_basic_mode()
            await self.test_jwt_mode()
            
        except Exception as e:
            print(f"Test failed with error: {e}")
        finally:
            await self.client.aclose()
        
        print("All tests completed!")


async def main():
    """Main test function."""
    tester = AuthModeTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())