# Policy Overview (Dev vs Prod)

This document describes the **centralized policy rules** enforced by SimpleSecCheck.
All environment-specific restrictions are defined in:

- `backend/app/services/policy_service.py`

**Related:** For the RBAC and permission model (Feature Flags → Permissions → Target Types → Scan Types), see [RBAC_AND_PERMISSIONS_DESIGN.md](RBAC_AND_PERMISSIONS_DESIGN.md).

## Why a Central Policy?

The policy service prevents scattered production checks by centralizing:

- what scan types are allowed
- whether local paths are permitted
- whether only Git/Docker Hub targets are allowed
- session/queue requirements
- UI feature flags

## Core Concepts

### Target Types

**Code Targets:**
- `LOCAL_MOUNT`: local filesystem path mounted into container (permissive only)
- `GIT_REPO`: git clone (all modes)
- `UPLOADED_CODE`: uploaded ZIP file extracted and mounted (all modes)

**Container Targets:**
- `CONTAINER_REGISTRY`: Container registry image (docker.io, ghcr.io, etc.; restricted: docker.io only)

**Application Targets:**
- `WEBSITE`: website URL scan (permissive only; disabled in restricted)
- `API_ENDPOINT`: REST/GraphQL API endpoint scan (permissive only; disabled in restricted)

**Infrastructure Targets:**
- `NETWORK_HOST`: network host/IP scan (permissive only; disabled in restricted)
- `KUBERNETES_CLUSTER`: live Kubernetes cluster scan (permissive only; disabled in restricted)

**Mobile Targets:**
- `APK`: Android APK file (all modes)
- `IPA`: iOS IPA file (all modes)

**Spec Targets:**
- `OPENAPI_SPEC`: OpenAPI/Swagger spec file for API fuzzing (all modes)

## Security modes (permissive vs restricted)

### Permissive (e.g. solo / self-hosted)

- ✅ Local paths allowed
- ✅ Git repos allowed
- ✅ Docker images allowed
- ✅ Website/Network scans allowed
- ✅ Bulk scan enabled
- ✅ Session management configurable
- ✅ Metadata collection **optional**

### Restricted (e.g. public or enterprise)

- ❌ Local paths **disabled** (admin can enable for self)
- ✅ Git repos allowed
- ✅ Docker images allowed **(Docker Hub only** in strict setups)
- ❌ Website/Network scans disabled (admin can enable for self)
- ❌ Bulk scan disabled (configurable)
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

- Adjust feature flags or USE_CASE (solo, network_intern, public_web, enterprise) to refine rules.
- For stricter enforcement, choose a restricted use case and extend `validate_scan_request()`.
