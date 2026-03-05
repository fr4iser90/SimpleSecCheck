# Frontend Security Considerations

## Security Features

### Non-Root Execution
- Frontend runs as user `frontend` (UID 1000), not root
- Matches scanner user for consistency
- No sudo privileges needed

### Read-Only Volumes
- All host volumes mounted read-only (`:ro`)
- Prevents accidental modification of:
  - CLI scripts (`scripts/`)
  - Results (`results/`)
  - Logs (`logs/`)
  - Config (`scanner/config/`)
  - Rules (`scanner/scanners/semgrep/rules/`)

### Docker Socket Access
- Docker socket mounted read-only (`:ro`)
- Only needed for `docker-compose` access
- WebUI doesn't directly interact with Docker API

### Process Security
- No `shell=True` in subprocess calls
- Command injection prevention
- No privilege escalation

### Container Security
- `no-new-privileges:true` - prevents privilege escalation
- `read_only: false` - only `/tmp` writable (for uvicorn)
- `tmpfs` for `/tmp` - no persistence, size limited

### Network Security
- Only exposes port 8080
- No external database connections
- No persistent state

## ⚠️ CRITICAL WARNING: NEVER EXPOSE PUBLICLY

**The Frontend should NEVER be exposed to the internet or public networks!**

### Why?
- Frontend can trigger security scans that deeply interact with your system
- No authentication by default
- Can execute Docker commands via `docker-compose`
- Access to scan results and logs

### Safe Usage
- ✅ **ONLY** use on `localhost` (127.0.0.1)
- ✅ **ONLY** use on trusted local networks
- ✅ Use reverse proxy with authentication if needed
- ❌ **NEVER** expose port 8080 publicly
- ❌ **NEVER** use without firewall protection
- ❌ **NEVER** use on untrusted networks

### Port Binding
```yaml
# ✅ SAFE - Only localhost
ports:
  - "127.0.0.1:8080:8080"

# ❌ DANGEROUS - Public access
ports:
  - "0.0.0.0:8080:8080"
  - "8080:8080"  # Defaults to 0.0.0.0
```

## Limitations

- **Docker Socket**: Required for `docker-compose` access. Consider using Docker API with proper authentication in production.
- **No Authentication**: WebUI has no authentication. For production, add:
  - Basic Auth
  - OAuth
  - API Keys
- **CORS**: Currently allows all origins. Restrict in production.
- Frontend includes auto-shutdown feature to prevent long-running instances (see below).

## Auto-Shutdown Feature

Frontend includes automatic shutdown to prevent long-running instances:

### Configuration (Environment Variables)

```bash
# Enable auto-shutdown after scan completes (default: true)
WEBUI_SHUTDOWN_AFTER_SCAN=true

# Shutdown delay after scan (seconds, default: 300 = 5 minutes)
WEBUI_SHUTDOWN_DELAY=300

# Idle timeout - shutdown if no activity (seconds, default: 1800 = 30 minutes)
WEBUI_IDLE_TIMEOUT=1800

# Disable auto-shutdown completely (NOT RECOMMENDED)
WEBUI_AUTO_SHUTDOWN=false
```

### Behavior

1. **After Scan Completion**: 
   - Waits `WEBUI_SHUTDOWN_DELAY` seconds after scan finishes
   - Allows time to view report
   - Then gracefully shuts down

2. **Idle Timeout**:
   - Tracks last activity (API calls, scan starts)
   - If no activity for `WEBUI_IDLE_TIMEOUT`, shuts down
   - Prevents forgotten instances

3. **Graceful Shutdown**:
   - Finishes current requests
   - Stops accepting new connections
   - Exits cleanly

### Why This Matters

- **Security**: Reduces attack window
- **Resource Usage**: Prevents forgotten instances
- **Single-Shot Principle**: WebUI should be temporary

## Docker Socket vs Docker API

### Current: Docker Socket (Read-Only)

**How it works:**
- WebUI calls the Python DockerRunner + orchestrator
- Uses `docker-compose` which needs Docker socket
- Socket mounted read-only (`:ro`)

**Security:**
- ✅ Read-only prevents write access
- ⚠️ Still allows Docker API calls (read-only)
- ⚠️ `docker-compose` has broad permissions

### Future: Docker API with Authentication

**Better approach:**
- Use Docker API directly instead of `docker-compose`
- Requires refactoring DockerRunner (Python)
- Can use TLS certificates for authentication
- More granular permission control

**Implementation (Future):**
```python
# Instead of subprocess.call(['docker-compose', ...])
# Use Docker SDK:
import docker

client = docker.DockerClient(
    base_url='unix://var/run/docker.sock',
    # With TLS in production:
    # tls=True,
    # tls_ca_cert='ca.pem',
    # tls_cert='cert.pem',
    # tls_key='key.pem'
)

# Create and run container directly
container = client.containers.run(...)
```

**Benefits:**
- ✅ Better authentication options
- ✅ More granular permissions
- ✅ No need for docker-compose binary
- ✅ Can use TLS certificates

**Trade-offs:**
- ⚠️ Requires refactoring existing scripts
- ⚠️ More complex implementation
- ⚠️ Need to handle container lifecycle manually

## Recommendations for Production

1. **Add Authentication**: Implement Basic Auth or OAuth
2. **Restrict CORS**: Set specific allowed origins
3. **HTTPS**: Use reverse proxy (nginx/traefik) with TLS
4. **Rate Limiting**: Prevent abuse
5. **Input Validation**: Additional validation for scan parameters
6. **Logging**: Audit log for all scan starts
7. **Auto-Shutdown**: Always enable (default)
8. **Localhost Only**: Never expose publicly
9. **Firewall**: Block port 8080 from external access
10. **Docker API**: Consider migrating to Docker API with TLS (future)

## Single-Shot Principle

WebUI follows single-shot principle:
- No database
- No persistent state
- Each scan is independent
- No history tracking
- **Auto-shutdown** prevents long-running instances

This reduces attack surface significantly.

## Best Practices for Local Usage

### 1. Start Only When Needed
```bash
# Start Frontend only when you need it
docker-compose --profile dev up

# Stop after use
docker-compose --profile dev down
```

### 2. Use Localhost Binding
```yaml
# docker-compose.yml - SAFE
ports:
  - "127.0.0.1:8080:8080"  # Only localhost
```

### 3. Enable Auto-Shutdown
```yaml
# docker-compose.yml
environment:
  - WEBUI_SHUTDOWN_AFTER_SCAN=true
  - WEBUI_IDLE_TIMEOUT=1800  # 30 minutes
```

### 4. Use Firewall
```bash
# Block external access (Linux)
sudo ufw deny 8080/tcp

# Or use iptables
sudo iptables -A INPUT -p tcp --dport 8080 ! -s 127.0.0.1 -j DROP
```

### 5. Monitor Running Instances
```bash
# Check if Frontend is running
docker ps | grep frontend

# Stop if forgotten
docker-compose --profile dev down
```

### 6. Never in Production Without:
- ✅ Authentication (Basic Auth minimum)
- ✅ HTTPS/TLS
- ✅ Reverse Proxy (nginx/traefik)
- ✅ Rate Limiting
- ✅ Firewall Rules
- ✅ Monitoring/Logging
