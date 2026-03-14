# Policy Overview (Dev vs Prod)

This document describes the **centralized policy rules** enforced by SimpleSecCheck.
All environment-specific restrictions are defined in:

- `backend/app/services/policy_service.py`

## Why a Central Policy?

The policy service prevents scattered production checks by centralizing:

- what scan types are allowed
- whether local paths are permitted
- whether only Git/Docker Hub targets are allowed
- session/queue requirements
- UI feature flags

## Core Concepts

### Environment

Set via:

```bash
ENVIRONMENT=dev|prod
```

### Target Types

**Code Targets:**
- `LOCAL_MOUNT`: local filesystem path mounted into container (dev only)
- `GIT_REPO`: git clone (dev + prod)
- `UPLOADED_CODE`: uploaded ZIP file extracted and mounted (dev + prod)

**Container Targets:**
- `CONTAINER_REGISTRY`: Container registry image (docker.io, ghcr.io, gcr.io, ECR, etc.) (dev + prod, prod: docker.io only)

**Application Targets:**
- `WEBSITE`: website URL scan (dev only, disabled in prod)
- `API_ENDPOINT`: REST/GraphQL API endpoint scan (dev only, disabled in prod)

**Infrastructure Targets:**
- `NETWORK_HOST`: network host/IP scan (dev only, disabled in prod)
- `KUBERNETES_CLUSTER`: live Kubernetes cluster scan (dev only, disabled in prod)

**Mobile Targets:**
- `APK`: Android APK file (dev + prod)
- `IPA`: iOS IPA file (dev + prod)

**Spec Targets:**
- `OPENAPI_SPEC`: OpenAPI/Swagger spec file for API fuzzing (dev + prod)

## Dev vs Prod Rules

### Dev (default)

- ✅ Local paths allowed
- ✅ Git repos allowed
- ✅ Docker images allowed
- ✅ Website/Network scans allowed
- ✅ Bulk scan enabled
- ✅ Session management **off** by default
- ✅ Metadata collection **optional**

### Prod

- ❌ Local paths **disabled**
- ✅ Git repos allowed
- ✅ Docker images allowed **(Docker Hub only)**
- ❌ Website/Network scans disabled
- ❌ Bulk scan disabled
- ✅ Session management **on**
- ✅ Queue required
- ✅ Metadata collection **always**

## Feature Flags from Policy

The UI gets its feature flags from `/api/config`, which calls:

```python
from app.services.policy_service import get_ui_features
```

## Scan Validation

All scan requests are validated centrally:

```python
from app.services.policy_service import validate_scan_request
```

This is used in:

- `routers/scan.py`
- `services/scan_service.py`
- `services/docker_runner.py`

## Central Configuration API

The policy service exposes:

- `get_policy_config()` – raw policy config
- `get_ui_features()` – UI feature flags
- `validate_scan_request()` – enforce prod/dev scan rules
- `is_session_required()` / `is_queue_required()`

## Notes

- Adjust `ONLY_GIT_SCANS`, `ZIP_UPLOAD_ENABLED`, or other env vars to refine prod rules.
- For stricter prod enforcement, extend `validate_scan_request()`.
