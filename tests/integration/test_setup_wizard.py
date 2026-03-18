"""
Integration Tests for Setup Wizard

Tests the complete setup flow:
1. Docker Compose startup
2. Extract setup token from logs
3. Verify setup token
4. Create admin user
5. Complete setup

Usage:
    pytest tests/integration/test_setup_wizard.py -v -s
    pytest tests/integration/test_setup_wizard.py::test_setup_flow -v -s
    pytest tests/integration/test_setup_wizard.py --cleanup -v -s
"""
import asyncio
import re
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any

import httpx
import pytest
import pytest_asyncio
import docker

# Test configuration
BASE_URL = "http://localhost:8080"
WORKER_API_URL = "http://localhost:8081"
TIMEOUT = 60
POLL_INTERVAL = 2
MAX_WAIT_TIME = 120  # Max time to wait for services to be ready


class DockerComposeManager:
    """Manages Docker Compose lifecycle for tests."""
    
    def __init__(self, compose_file: str = "docker-compose.yml"):
        self.compose_file = compose_file
        self.project_dir = Path(__file__).parent.parent.parent
        self.compose_cmd = ["docker", "compose", "-f", str(self.project_dir / compose_file)]
    
    def _run_compose(self, command: list, check: bool = True) -> subprocess.CompletedProcess:
        """Run docker compose command."""
        cmd = self.compose_cmd + command
        result = subprocess.run(
            cmd,
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    
    def up(self, build: bool = False, detach: bool = True) -> subprocess.CompletedProcess:
        """Start services."""
        cmd = ["up"]
        if build:
            cmd.append("--build")
        if detach:
            cmd.append("-d")
        return self._run_compose(cmd)
    
    def down(self, volumes: bool = False) -> subprocess.CompletedProcess:
        """Stop services."""
        cmd = ["down"]
        if volumes:
            cmd.append("-v")
        return self._run_compose(cmd)
    
    def logs(self, service: Optional[str] = None, tail: int = 100) -> str:
        """Get logs from services."""
        cmd = ["logs", "--tail", str(tail)]
        if service:
            cmd.append(service)
        result = self._run_compose(cmd, check=False)
        return result.stdout
    
    def ps(self) -> subprocess.CompletedProcess:
        """List running services."""
        return self._run_compose(["ps"])
    
    def wait_for_services(self, services: list[str], timeout: int = MAX_WAIT_TIME) -> bool:
        """Wait for services to be healthy."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.ps()
            if result.returncode != 0:
                time.sleep(POLL_INTERVAL)
                continue
            
            # Check if all services are running
            running_services = []
            for line in result.stdout.split('\n'):
                if 'Up' in line or 'running' in line.lower():
                    for service in services:
                        if service in line:
                            running_services.append(service)
            
            if len(set(running_services)) >= len(services):
                # Additional check: services are actually responding
                if self._check_services_ready(services):
                    return True
            
            time.sleep(POLL_INTERVAL)
        
        return False
    
    def _check_services_ready(self, services: list[str]) -> bool:
        """Check if services are actually ready (not just running)."""
        checks = {
            "backend": lambda: self._check_http(f"{BASE_URL}/api/health"),
            "worker": lambda: self._check_http(f"{WORKER_API_URL}/api/scanners"),
            "redis": lambda: self._check_redis(),
            "postgres": lambda: self._check_postgres(),
            "frontend": lambda: self._check_http(f"{BASE_URL}/"),
        }
        
        for service in services:
            if service in checks:
                try:
                    if not checks[service]():
                        return False
                except Exception:
                    return False
        
        return True
    
    def _check_http(self, url: str) -> bool:
        """Check if HTTP service is responding."""
        try:
            response = httpx.get(url, timeout=5)
            return response.status_code < 500
        except Exception:
            return False
    
    def _check_redis(self) -> bool:
        """Check if Redis is responding."""
        try:
            client = docker.from_env()
            containers = client.containers.list(filters={"name": "redis"})
            if containers:
                return containers[0].status == "running"
        except Exception:
            pass
        return False
    
    def _check_postgres(self) -> bool:
        """Check if Postgres is responding."""
        try:
            client = docker.from_env()
            containers = client.containers.list(filters={"name": "postgres"})
            if containers:
                return containers[0].status == "running"
        except Exception:
            pass
        return False


def extract_setup_token_from_logs(logs: str) -> Optional[str]:
    """Extract setup token from backend logs."""
    # Pattern: "Setup Token: <token>"
    pattern = r"Setup Token:\s+([a-f0-9]{64})"
    match = re.search(pattern, logs)
    if match:
        return match.group(1)
    
    # Alternative pattern in JSON logs
    pattern_json = r'"message":\s*"Setup token generated"'
    if re.search(pattern_json, logs):
        # Token might be in a different format, try to find it
        pattern_token = r'"token":\s*"([^"]+)"'
        match = re.search(pattern_token, logs)
        if match:
            return match.group(1)
    
    return None


@pytest.fixture(scope="function")
def docker_compose(request):
    """Docker Compose fixture with automatic cleanup."""
    cleanup = request.config.getoption("--cleanup", default=False)
    manager = DockerComposeManager()
    
    # Cleanup before test if requested
    if cleanup:
        manager.down(volumes=True)
        time.sleep(2)
    
    # Start services
    print("\n🚀 Starting Docker Compose...")
    manager.up(build=True, detach=True)
    
    # Wait for services to be ready
    services = ["backend", "worker", "redis", "postgres", "frontend"]
    print(f"⏳ Waiting for services to be ready: {', '.join(services)}...")
    
    if not manager.wait_for_services(services, timeout=MAX_WAIT_TIME):
        logs = manager.logs()
        print(f"❌ Services failed to start. Logs:\n{logs}")
        manager.down(volumes=cleanup)
        pytest.fail("Services failed to start within timeout")
    
    print("✅ All services are ready!")
    
    yield manager
    
    # Cleanup after test
    print(f"\n🧹 Cleaning up Docker Compose (volumes: {cleanup})...")
    manager.down(volumes=cleanup)
    time.sleep(2)


@pytest_asyncio.fixture
async def api_client():
    """HTTP client for API requests."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture
async def worker_client():
    """HTTP client for Worker API requests."""
    async with httpx.AsyncClient(base_url=WORKER_API_URL, timeout=TIMEOUT) as client:
        yield client


class SetupWizardTester:
    """Helper class for testing setup wizard flow."""
    
    def __init__(self, api_client: httpx.AsyncClient, docker_manager: DockerComposeManager):
        self.api_client = api_client
        self.docker_manager = docker_manager
        self.setup_token: Optional[str] = None
        self.session_id: Optional[str] = None
    
    async def extract_setup_token(self) -> str:
        """Extract setup token from backend logs."""
        print("📋 Extracting setup token from logs...")
        
        # Wait for backend to fully start and generate token
        max_attempts = 15
        for attempt in range(max_attempts):
            await asyncio.sleep(2)
            logs = self.docker_manager.logs(service="backend", tail=500)
            token = extract_setup_token_from_logs(logs)
            
            if token:
                # Found token in logs, now wait for DB and Redis to be ready
                # The token is stored AFTER create_tables() is called
                # So we need to wait for the DB to be ready
                print(f"✅ Found setup token in logs: {token[:16]}...")
                print("   Waiting for database and Redis to be ready...")
                
                # PROFESSIONELL: Warte auf Health Check statt Sleep!
                max_health_checks = 20
                for health_attempt in range(max_health_checks):
                    try:
                        response = await self.api_client.get("/ready")
                        if response.status_code == 200:
                            health_data = response.json()
                            if health_data.get("status") == "ready":
                                print("   ✅ Database and Redis are ready!")
                                # Warte 10 Sekunden vor der ersten Prüfung
                                print("   ⏳ Waiting 10 seconds before first token verification...")
                                await asyncio.sleep(10)
                                self.setup_token = token
                                return token
                    except Exception as e:
                        # Health check failed, continue waiting
                        pass
                    
                    if health_attempt < max_health_checks - 1:
                        await asyncio.sleep(1)
                
                # If health check never succeeded, still return token (fallback)
                print("   ⚠️ Health check timeout, proceeding anyway...")
                # Warte auch hier 10 Sekunden
                print("   ⏳ Waiting 10 seconds before first token verification...")
                await asyncio.sleep(10)
                self.setup_token = token
                return token
            
            if attempt < max_attempts - 1:
                print(f"   Attempt {attempt + 1}/{max_attempts}: Token not found yet, waiting...")
        
        # Last attempt with more logs
        logs = self.docker_manager.logs(service="backend", tail=1000)
        token = extract_setup_token_from_logs(logs)
        
        if not token:
            # Debug: show what we found in logs
            print(f"❌ Could not extract token. Last 500 chars of logs:")
            print(logs[-500:])
            raise ValueError("Could not extract setup token from logs")
        
        # Wait for health check before returning
        print("   Waiting for database and Redis to be ready...")
        max_health_checks = 20
        health_ready = False
        for health_attempt in range(max_health_checks):
            try:
                response = await self.api_client.get("/ready")
                if response.status_code == 200:
                    health_data = response.json()
                    if health_data.get("status") == "ready":
                        print("   ✅ Database and Redis are ready!")
                        health_ready = True
                        break
            except Exception:
                pass
            
            if health_attempt < max_health_checks - 1:
                await asyncio.sleep(1)
        
        # Warte 10 Sekunden vor der ersten Prüfung
        if health_ready:
            print("   ⏳ Waiting 10 seconds before first token verification...")
            await asyncio.sleep(10)
        else:
            print("   ⚠️ Health check timeout, waiting 10 seconds anyway...")
            await asyncio.sleep(10)
        
        print(f"✅ Found setup token: {token[:16]}...")
        self.setup_token = token
        return token
    
    async def verify_token(self, token: str) -> str:
        """Verify setup token and get session ID."""
        print("🔐 Verifying setup token...")
        
        # Retry verification multiple times - the token might not be in DB yet
        max_retries = 10
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = await self.api_client.post(
                    "/api/setup/verify",
                    headers={"X-Setup-Token": token},
                    json={}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    assert "session_id" in data, "No session_id in response"
                    
                    self.session_id = data["session_id"]
                    print(f"✅ Token verified, session ID: {self.session_id[:16]}...")
                    return self.session_id
                elif response.status_code == 400:
                    # Token invalid or not in DB yet
                    error_text = response.text
                    last_error = f"Status {response.status_code}: {error_text}"
                    
                    # If it's "No setup token available", the table might not exist yet
                    if "No setup token available" in error_text:
                        if attempt < max_retries - 1:
                            print(f"   Attempt {attempt + 1}/{max_retries}: Token not in DB yet, waiting for table creation...")
                            await asyncio.sleep(3)
                            continue
                    
                    # If it's "Invalid or expired", might be timing issue
                    if "Invalid or expired" in error_text:
                        if attempt < max_retries - 1:
                            print(f"   Attempt {attempt + 1}/{max_retries}: Token verification failed, retrying...")
                            await asyncio.sleep(3)
                            continue
                    
                    # Other 400 error
                    if attempt < max_retries - 1:
                        print(f"   Attempt {attempt + 1}/{max_retries} failed: {last_error}, retrying...")
                        await asyncio.sleep(3)
                else:
                    last_error = f"Status {response.status_code}: {response.text}"
                    if attempt < max_retries - 1:
                        print(f"   Attempt {attempt + 1}/{max_retries} failed: {last_error}, retrying...")
                        await asyncio.sleep(2)
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    print(f"   Attempt {attempt + 1}/{max_retries} failed: {last_error}, retrying...")
                    await asyncio.sleep(2)
        
        # All retries failed - show debug info
        print(f"\n❌ Token verification failed after {max_retries} attempts")
        print(f"   Last error: {last_error}")
        print(f"   Token (first 16 chars): {token[:16]}...")
        
        # Try to get backend logs for debugging
        try:
            logs = self.docker_manager.logs(service="backend", tail=100)
            print(f"   Recent backend logs (last 100 lines):")
            print(logs[-500:])
        except Exception:
            pass
        
        raise AssertionError(f"Token verification failed after {max_retries} attempts: {last_error}")
    
    async def check_setup_status(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Check setup status."""
        headers = {}
        if session_id:
            headers["X-Setup-Session"] = session_id
        
        response = await self.api_client.get("/api/setup/status", headers=headers)
        assert response.status_code == 200, f"Status check failed: {response.text}"
        return response.json()
    
    async def initialize_setup(
        self,
        admin_username: str = "testadmin",
        admin_email: str = "admin@test.example",
        admin_password: str = "TestPass123!",
        system_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initialize setup with admin user and system config."""
        print("⚙️ Initializing setup...")
        
        if not self.session_id:
            raise ValueError("No session ID. Call verify_token() first.")
        
        if system_config is None:
            system_config = {
                "auth_mode": "free",
                "scanner_timeout": 300,
                "max_concurrent_scans": 3
            }
        
        response = await self.api_client.post(
            "/api/setup/initialize",
            headers={"X-Setup-Session": self.session_id},
            json={
                "admin_user": {
                    "username": admin_username,
                    "email": admin_email,
                    "password": admin_password
                },
                "system_config": system_config
            }
        )
        
        assert response.status_code == 200, f"Setup initialization failed: {response.text}"
        data = response.json()
        print(f"✅ Setup initialized, admin user ID: {data.get('admin_user_id')}")
        return data
    
    async def complete_setup_flow(
        self,
        admin_username: str = "testadmin",
        admin_email: str = "admin@test.example",
        admin_password: str = "TestPass123!",
        system_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Complete the full setup flow."""
        # Extract token
        token = await self.extract_setup_token()
        
        # Verify token
        session_id = await self.verify_token(token)
        
        # Check status
        status = await self.check_setup_status(session_id)
        assert not status.get("setup_complete"), "Setup should not be complete yet"
        
        # Initialize setup
        result = await self.initialize_setup(
            admin_username=admin_username,
            admin_email=admin_email,
            admin_password=admin_password,
            system_config=system_config
        )
        
        # Verify setup is complete
        final_status = await self.check_setup_status()
        assert final_status.get("setup_complete"), "Setup should be complete"
        
        return result


@pytest.mark.asyncio
async def test_setup_flow_free_auth(api_client, docker_compose):
    """Setup flow with auth_mode free."""
    tester = SetupWizardTester(api_client, docker_compose)
    result = await tester.complete_setup_flow(
        admin_username="testadmin",
        admin_email="admin@test.example",
        admin_password="TestPass123!",
        system_config={
            "auth_mode": "free",
            "scanner_timeout": 300,
            "max_concurrent_scans": 3
        },
    )
    assert result["success"] is True
    assert "admin_user_id" in result
    print("✅ Setup flow completed (free auth).")


@pytest.mark.asyncio
async def test_setup_flow_session_auth(api_client, docker_compose):
    """Setup flow with auth_mode session."""
    tester = SetupWizardTester(api_client, docker_compose)
    result = await tester.complete_setup_flow(
        admin_username="sessionadmin",
        admin_email="admin@session.example",
        admin_password="SessionPass123!",
        system_config={
            "auth_mode": "session",
            "scanner_timeout": 600,
            "max_concurrent_scans": 5
        },
    )
    assert result["success"] is True
    assert "admin_user_id" in result
    print("✅ Setup flow completed (session auth).")


@pytest.mark.asyncio
async def test_setup_token_extraction(api_client, docker_compose):
    """Test setup token extraction from logs."""
    tester = SetupWizardTester(api_client, docker_compose)
    
    token = await tester.extract_setup_token()
    assert token is not None
    assert len(token) == 64, "Token should be 64 characters (SHA256 hex)"
    print(f"✅ Token extraction works: {token[:16]}...")


@pytest.mark.asyncio
async def test_setup_token_verification(api_client, docker_compose):
    """Test setup token verification."""
    tester = SetupWizardTester(api_client, docker_compose)
    
    token = await tester.extract_setup_token()
    session_id = await tester.verify_token(token)
    
    assert session_id is not None
    assert len(session_id) > 0
    print("✅ Token verification works!")


@pytest.mark.asyncio
async def test_setup_status_check(api_client, docker_compose):
    """Test setup status check."""
    tester = SetupWizardTester(api_client, docker_compose)
    
    status = await tester.check_setup_status()
    
    assert "setup_required" in status
    assert "setup_complete" in status
    assert "database_connected" in status
    assert status["database_connected"] is True
    print("✅ Status check works!")


@pytest.mark.asyncio
async def test_invalid_token(api_client, docker_compose):
    """Test that invalid token is rejected."""
    print("🔐 Testing invalid token rejection...")
    
    response = await api_client.post(
        "/api/setup/verify",
        headers={"X-Setup-Token": "invalid_token_12345"},
        json={}
    )
    
    assert response.status_code == 401, "Invalid token should be rejected"
    print("✅ Invalid token correctly rejected!")


@pytest.mark.asyncio
async def test_setup_without_session(api_client, docker_compose):
    """Test that setup initialization requires session."""
    print("🔐 Testing setup without session...")
    
    response = await api_client.post(
        "/api/setup/initialize",
        json={
            "admin_user": {
                "username": "test",
                "email": "test@test.com",
                "password": "Test123!"
            },
            "system_config": {}
        }
    )
    
    assert response.status_code == 401, "Setup without session should be rejected"
    print("✅ Setup without session correctly rejected!")


@pytest.mark.asyncio
async def test_setup_then_login_and_cookies(api_client, docker_compose):
    """
    E2E: Server up → complete setup → login → check logged in, cookies, and setup status cache.
    Ensures no 503 after setup, refresh_token cookie is set, and /api/setup/status reports setup_complete.
    """
    admin_email = "admin@test.example"
    admin_password = "TestPass123!"
    tester = SetupWizardTester(api_client, docker_compose)

    # 1. Complete setup (server already up via fixture)
    await tester.complete_setup_flow(
        admin_username="testadmin",
        admin_email=admin_email,
        admin_password=admin_password,
        system_config={"auth_mode": "free", "scanner_timeout": 300, "max_concurrent_scans": 3},
    )
    print("✅ Setup completed")

    # 2. Login must succeed (no 503 "Setup required" – middleware cache fixed)
    login_resp = await api_client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    assert login_resp.status_code == 200, (
        f"Login should succeed after setup, got {login_resp.status_code}: {login_resp.text}"
    )
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data.get("email") == admin_email
    print("✅ Login OK, access_token received")

    # 3. Refresh token cookie must be set (HttpOnly cookie from backend)
    refresh_cookie = login_resp.cookies.get("refresh_token")
    assert refresh_cookie is not None and len(refresh_cookie) > 0, (
        "refresh_token cookie should be set on login"
    )
    print("✅ refresh_token cookie present")

    # 4. Setup status must report complete (cache/DB correct)
    status_resp = await api_client.get("/api/setup/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data.get("setup_complete") is True, (
        f"setup_complete should be True after setup, got {status_data}"
    )
    print("✅ /api/setup/status reports setup_complete=True")

    # 5. Refresh endpoint with cookie must return new access token (same client sends cookie)
    refresh_resp = await api_client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200, (
        f"Refresh with cookie should succeed, got {refresh_resp.status_code}: {refresh_resp.text}"
    )
    refresh_data = refresh_resp.json()
    assert "access_token" in refresh_data
    print("✅ /api/v1/auth/refresh with cookie OK")

    print("✅ E2E setup→login→cookies→cache check passed!")


# pytest_addoption is defined in tests/conftest.py
