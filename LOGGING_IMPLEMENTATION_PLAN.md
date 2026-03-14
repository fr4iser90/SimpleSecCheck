Based on the current output, I can identify exactly which lines need to be changed to achieve the clean format you want. Here's the breakdown:

## Lines that need to be REMOVED (verbose output):

**Worker Service (lines to remove):**
```
SimpleSecCheck_worker    | 2026-03-13 00:56:02,468 - __main__ - INFO - Queue type: redis
SimpleSecCheck_worker    | 2026-03-13 00:56:02,468 - __main__ - INFO - Database connection: postgresql+asyncpg://simpleseccheck:simpleseccheck@localhost/simpleseccheck
SimpleSecCheck_worker    | 2026-03-13 00:56:02,470 - worker.infrastructure.docker_adapter - WARNING - Continuing without Docker functionality - some features may not work
SimpleSecCheck_worker    | 2026-03-13 00:56:02,494 - worker.infrastructure.queue_adapter - INFO - Initialized Redis queue adapter
SimpleSecCheck_worker    | 2026-03-13 00:56:02,494 - __main__ - INFO - Worker services initialized successfully
SimpleSecCheck_worker    | 2026-03-13 00:56:02,494 - __main__ - INFO - Starting worker in foreground mode
SimpleSecCheck_worker    | 2026-03-13 00:56:02,494 - worker.domain.job_execution.services.job_orchestration_service - INFO - Starting job orchestration worker
```

**Backend Service (lines to remove):**
```
SimpleSecCheck_backend   | SimpleSecCheck API starting up
SimpleSecCheck_backend   | /app/backend/api/services/setup_token_service.py:89: RuntimeWarning: coroutine 'DatabaseAdapter.get_session' was never awaited
SimpleSecCheck_backend   |   async with db_adapter.get_session() as session:
SimpleSecCheck_backend   | RuntimeWarning: Enable tracemalloc to get the object allocation traceback
SimpleSecCheck_backend   | Error storing setup token: 'coroutine' object does not support the asynchronous context manager protocol
SimpleSecCheck_backend   | 
SimpleSecCheck_backend   | === SETUP TOKEN ===
SimpleSecCheck_backend   | Setup Token: 3f1c7d6cad79e22137bb3861400d913198398fc4e57cb4d5b8f98c1edc2202b2
SimpleSecCheck_backend   | Expires in: 24 hours
SimpleSecCheck_backend   | Use this token in the setup wizard.
SimpleSecCheck_backend   | ==================
SimpleSecCheck_backend   | 
SimpleSecCheck_backend   | Setup token generated successfully
SimpleSecCheck_backend   | Allowing health check: /api/health
SimpleSecCheck_backend   | Request started: GET /api/health
SimpleSecCheck_backend   | Request completed: GET /api/health 200
```

**Frontend Service (lines to remove):**
```
SimpleSecCheck_frontend  | /docker-entrypoint.sh: /docker-entrypoint.d/ is not empty, will attempt to perform configuration
SimpleSecCheck_frontend  | /docker-entrypoint.sh: Looking for shell scripts in /docker-entrypoint.d/
SimpleSecCheck_frontend  | /docker-entrypoint.sh: Launching /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
SimpleSecCheck_frontend  | 10-listen-on-ipv6-by-default.sh: info: Getting the checksum of /etc/nginx/conf.d/default.conf
SimpleSecCheck_frontend  | 10-listen-on-ipv6-by-default.sh: info: /etc/nginx/conf.d/default.conf differs from the packaged version
SimpleSecCheck_frontend  | /docker-entrypoint.sh: Sourcing /docker-entrypoint.d/15-local-resolvers.envsh
SimpleSecCheck_frontend  | /docker-entrypoint.sh: Launching /docker-entrypoint.d/20-envsubst-on-templates.sh
SimpleSecCheck_frontend  | /docker-entrypoint.sh: Launching /docker-entrypoint.d/30-tune-worker-processes.sh
SimpleSecCheck_frontend  | /docker-entrypoint.sh: Configuration complete; ready for start up
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: using the "epoll" event method
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: nginx/1.27.5
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: built by gcc 14.2.0 (Alpine 14.2.0) 
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: OS: Linux 6.18.0
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: getrlimit(RLIMIT_NOFILE): 1024:524288
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker processes
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 29
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 30
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 31
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 32
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 33
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 34
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 35
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 36
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 37
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 38
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 39
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 40
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 41
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 42
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 43
SimpleSecCheck_frontend  | 2026/03/13 00:56:07 [notice] 1#1: start worker process 44
```

## Lines that should REMAIN and be formatted as:

**Worker Service (keep and format):**
```
[Worker] Starting SimpleSecCheck Worker
[Worker] Max concurrent jobs: 3
```

**Backend Service (keep and format):**
```
[Backend] API started successfully
[Backend] Setup token generated: 3f1c7d6cad79e22137bb3861400d913198398fc4e57cb4d5b8f98c1edc2202b2
```

**Database Services (keep and format):**
```
[Redis] Ready to accept connections
[Postgres] Ready to accept connections
```

The key changes needed are:
1. **Remove all verbose Docker entrypoint messages**
2. **Remove all Nginx worker process startup messages**
3. **Remove all detailed logging with timestamps and module paths**
4. **Keep only essential service status messages**
5. **Format everything as `[Service] Event: Details`**

Would you like me to proceed with implementing these specific changes?