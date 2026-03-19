# SimpleSecCheck Worker

The worker component of SimpleSecCheck is responsible for executing security scans in isolated Docker containers and processing their results.

## Overview

The worker acts as the job orchestrator that:
- Listens for scan jobs from the queue
- Starts scanner containers for each job
- Monitors container execution
- Collects and processes scan results
- Manages job lifecycle and status tracking

## Architecture

### Domain Layer (`domain/job_execution/`)
- **Entities**: Pure business objects (JobExecution, ContainerSpec, ExecutionResult)
- **Services**: Business logic without infrastructure dependencies (JobOrchestrationService, ResultProcessingService)
- **Repositories (Interfaces)**: Contracts for data access without implementation details

### Infrastructure Layer (`infrastructure/`)
- **Database**: Database adapters and repository implementations
- **Docker**: Docker container management and orchestration
- **Queue**: Message queue adapters for job processing
- **Adapters**: External system integrations

### CLI Layer (`cli/`)
- **worker_main.py**: Dependency injection and service assembly
- **Entry point**: Command-line interface for starting the worker

## Responsibilities

### Job Queue Processing
- Polls Redis or memory-based queue for new scan jobs
- Processes jobs sequentially or in parallel (configurable concurrency)
- Handles job failures and retries

### Container Orchestration
- Starts scanner containers with proper configuration
- Monitors container lifecycle and health
- Stops containers on errors or timeouts
- Collects container logs and outputs

### Result Processing
- Aggregates scan results from container outputs
- Processes structured and unstructured data
- Stores results in database with proper formatting
- Generates summaries and metrics

### Status Management
- Tracks job status in real-time (pending → running → completed/failed)
- Manages container state transitions
- Provides health checks and monitoring endpoints
- Handles resource cleanup and garbage collection

## Workflow

### 1. Job Reception
```
Queue → Worker → Job Data Extraction → Job Execution Creation
```

### 2. Container Execution
```
Container Start → Mount Volumes → Execute Scan → Monitor Progress → Collect Results
```

### 3. Result Processing
```
Raw Results → Parse & Validate → Structure Data → Store in Database → Generate Summary
```

### 4. Cleanup
```
Stop Container → Remove Temporary Files → Update Job Status → Free Resources
```

## Docker Usage

### Build Image
```bash
docker build -t simpleseccheck/worker:latest .
```

### Run Container
```bash
docker run -d \
  --name simpleseccheck-worker \
  --restart unless-stopped \
  -e REDIS_URL=redis://redis:6379 \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_USER=ssc_user \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=simpleseccheck \
  -e MAX_CONCURRENT_JOBS=3 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /app/results:/app/results \
  simpleseccheck/worker:latest
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string (queue is always Redis) |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | — | Database (no `DATABASE_URL`) |
| `MAX_CONCURRENT_JOBS` | `3` | Maximum parallel job executions |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `RESULTS_DIR` | `/app/results` | Directory for scan results |

### Docker Compose
```yaml
worker:
  build: ./worker
  environment:
    - REDIS_URL=redis://redis:6379
    - POSTGRES_HOST=postgres
    - POSTGRES_PORT=5432
    - POSTGRES_USER=ssc_user
    - POSTGRES_PASSWORD=changeme
    - POSTGRES_DB=simpleseccheck
    - MAX_CONCURRENT_JOBS=3
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
    - ./results:/app/results
  depends_on:
    - redis
    - postgres
```

## Configuration

### Queue Configuration
- **Redis**: always used in production (`REDIS_URL` / `QUEUE_CONNECTION`). No `QUEUE_TYPE` env.
- **Memory**: optional via CLI `--queue-type memory` for local debugging only.

### Database Configuration
- **PostgreSQL**: recommended for durable jobs

### Resource Limits
```bash
# Limit memory and CPU for scanner containers
-e SCANNER_MEMORY_LIMIT=2g
-e SCANNER_CPU_LIMIT=1.0
```

## Health Checks & Monitoring

### Health Endpoint
The worker provides health check endpoints:
```
GET /health - Overall worker status
GET /health/jobs - Active job count
GET /health/queue - Queue status
```

### Logging
```bash
# View worker logs
docker logs simpleseccheck-worker

# Follow logs in real-time
docker logs -f simpleseccheck-worker

# Filter by log level
docker logs simpleseccheck-worker 2>&1 | grep ERROR
```

### Metrics
The worker exposes metrics for:
- Active job count
- Job completion rate
- Queue depth
- Container resource usage
- Error rates

### Monitoring Commands
```bash
# Check worker status
docker ps | grep worker

# View resource usage
docker stats simpleseccheck-worker

# Check queue status
redis-cli llen job_queue

# Monitor logs
docker logs -f simpleseccheck-worker --tail 100
```

## Troubleshooting

### Common Issues

1. **Permission Denied on Docker Socket**
   ```bash
   # Ensure worker user can access docker socket
   docker exec simpleseccheck-worker id
   docker exec simpleseccheck-worker ls -la /var/run/docker.sock
   ```

2. **Database Connection Failed**
   ```bash
   # Check database connectivity
   docker exec simpleseccheck-worker nc -zv postgres 5432
   ```

3. **Queue Not Processing**
   ```bash
   # Check queue contents
   docker exec simpleseccheck-worker redis-cli llen job_queue
   ```

4. **Container Startup Failures**
   ```bash
   # Check scanner container logs
   docker logs <scanner-container-id>
   ```

### Debug Mode
```bash
# Enable debug logging
docker run -e LOG_LEVEL=DEBUG simpleseccheck/worker:latest

# Run with interactive shell
docker run -it --entrypoint /bin/bash simpleseccheck/worker:latest
```

## Development

### Local Testing
```bash
# Run worker locally
python worker/cli/worker_main.py --queue-type memory --log-level DEBUG

# Test with specific configuration
python worker/cli/worker_main.py \
  --queue-type redis \
  --queue-connection redis://localhost:6379 \
  --max-concurrent-jobs 1
```

### Adding New Scanner Support
1. Create scanner plugin in `scanner/plugins/`
2. Register scanner in `scanner/core/scanner_registry.py`
3. Update worker configuration if needed
4. Test with sample projects

## Security Considerations

- Worker runs with Docker socket access - limit to trusted networks
- Scanner containers are isolated but monitor resource usage
- Results directory should have proper permissions
- Use secrets management for database credentials
- Enable TLS for database connections over untrusted networks