# RBAC & Permissions Design

This document describes the target architecture for **Feature Flags**, **RBAC (Roles + Permissions)**, **Target Types**, and **Scan Types** in SimpleSecCheck. It is the single source of truth for the permission model and should guide implementation.

See also: [POLICY.md](POLICY.md) for current policy/feature-flag overview.

---

## 1. Layer Model

Responsibility is split into four layers:

| Layer | Question | Owned by |
|-------|----------|----------|
| **Feature Flags** | Does the system support this? | System / Use Case / Admin Settings |
| **Permissions (RBAC)** | Is the user allowed to do this? | Role (and optionally user overrides) |
| **Target Types** | What is being scanned? | Domain (`TargetType` enum) |
| **Scan Types** | Which analysis runs? | Scanners / Scan configuration |

Flow:

```
Feature Flag (enabled?)
       ↓
Permission (user has permission?)
       ↓
Target Type (what is scanned)
       ↓
Scan Types (which analyses)
       ↓
Queue / Execution
```

This avoids permission explosion (e.g. no `scan_git_secret`, `scan_zip_dependency`); instead: one permission per target type, and scan types are chosen per target.

---

## 2. Feature Flags (System Capabilities)

Global flags control **whether the system allows** a capability at all. They do **not** define who may use it.

Current flags (from settings / use case):

- `ALLOW_LOCAL_PATHS`
- `ALLOW_GIT_REPOS`
- `ALLOW_ZIP_UPLOAD`
- `ALLOW_REMOTE_CONTAINERS`
- `ALLOW_NETWORK_SCANS`

Rule: **Feature Flags stay global.** They answer: “Is this capability enabled in this deployment?”

---

## 3. Target Type → Permission Mapping

One permission per “controllable” target type. Naming convention:

- **Permission name:** `scan_<target_type>` (use existing `TargetType` value where it fits).
- Optional explicit map for display names (e.g. `local_mount` → `scan_local_path` in UI).

Proposed mapping (aligned with `backend/domain/entities/target_type.py`):

| Target Type (enum value) | Permission | Notes |
|--------------------------|------------|--------|
| `git_repo` | `scan_git_repo` | |
| `uploaded_code` | `scan_zip_upload` | ZIP upload |
| `local_mount` | `scan_local_path` | **Dangerous** – admin only by default |
| `container_registry` | `scan_container_registry` | |
| `website` | `scan_website` | |
| `api_endpoint` | `scan_api_endpoint` | |
| `network_host` | `scan_network_target` | |
| `kubernetes_cluster` | `scan_kubernetes_cluster` | |
| `apk` | `scan_apk` | |
| `ipa` | `scan_ipa` | |
| `openapi_spec` | `scan_openapi_spec` | |

Helper (conceptual):

```python
def permission_for_target(target_type: str) -> str:
    # Optional map for naming (e.g. local_mount → scan_local_path)
    return f"scan_{target_type}"  # or use TARGET_PERMISSION_MAP
```

---

## 4. Dangerous Targets

Targets that imply host/network access or high risk must be explicitly marked and restricted (e.g. admin-only by default).

**Dangerous targets (example):**

- `local_mount` – host filesystem access
- (Future: e.g. `docker_socket` if added)

In UI and policy:

- Show a warning (e.g. ⚠) next to these options.
- Default role: only Admin (or a dedicated role) gets the corresponding permission.

---

## 5. Feature Flag + Permission Check

Access to a target type is allowed only if **both** are true:

1. **Feature flag** for that capability is enabled (e.g. `ALLOW_LOCAL_PATHS`).
2. **User has the permission** for that target (e.g. `scan_local_path`).

Pseudocode:

```python
if not feature_enabled_for_target(target_type):
    raise FeatureDisabled()
if not user.has_permission(permission_for_target(target_type)):
    raise PermissionDenied()
```

---

## 6. Target Types vs Scan Types (Decoupling)

- **Target type** = source of the scan (git repo, ZIP, container image, local path, etc.).
- **Scan type** = kind of analysis (secret scan, dependency scan, SAST, container scan, etc.).

A target type supports a **set of scan types**; this mapping should be configurable, not hardcoded in permissions.

Example:

- `git_repo` → e.g. `secret_scan`, `dependency_scan`, `sast`
- `container_registry` → e.g. `container_scan`, `secret_scan`

So: **Permissions are per target type.** Which scan types run for that target is a separate configuration (e.g. `TARGET_SCAN_SUPPORT` or scanner registry).

---

## 7. Naming Conventions

- **Target types:** snake_case, from `TargetType` enum (`git_repo`, `local_mount`, `container_registry`, …).
- **Permissions:** `scan_<target_type>` with optional display aliases (e.g. `scan_local_path` for `local_mount`).
- **Feature flags:** existing `ALLOW_*` names.

Keep one consistent convention so helpers like `permission = f"scan_{target_type}"` stay valid where no alias is needed.

---

## 8. Roles for Version 1

Start with **3 roles**, no per-user permission overrides:

| Role | Permissions (example) |
|------|------------------------|
| **Admin** | All permissions (including `scan_local_path`, `manage_users`, `manage_settings`, etc.) |
| **User** | `scan_git_repo`, `scan_zip_upload`, `scan_container_registry`, `view_own_scans`, `export_scans` |
| **Restricted** | `scan_git_repo`, `view_own_scans` |

- **Admin** = full access + dangerous targets.
- **User** = standard scan targets, no local path.
- **Restricted** = minimal (e.g. Git only).

User overrides (e.g. “User X gets `scan_container_registry` even if role is Restricted”) can be added later.

---

## 9. Optional: Target Security Level

For UI and policy, targets can be tagged by risk:

- **safe:** e.g. `git_repo`, `zip_upload`
- **restricted:** e.g. `container_registry`, `network_host`
- **dangerous:** e.g. `local_mount`

This helps admins understand impact and allows policies like “only show dangerous targets to admin”.

---

## 10. Data Model (Target State for Implementation)

When implementing RBAC:

- **roles** – id, name, description
- **permissions** – id, name, description (e.g. `scan_git_repo`, `scan_local_path`)
- **role_permissions** – role_id, permission_id
- **users** – existing user table + `role_id`

Optional later:

- **user_permissions** – user_id, permission_id (overrides for specific users)

Check logic:

- `user.has_permission("scan_git_repo")` → resolve via `user.role.permissions` (and optional `user_permissions`).

---

## 11. End-to-End Flow (Example)

User starts a scan:

1. **Target type:** e.g. `git_repo`
2. **Scan types:** e.g. secret_scan, dependency_scan

Checks:

1. Feature flag for Git enabled? (e.g. `ALLOW_GIT_REPOS`)
2. User has permission `scan_git_repo`?
3. Selected scan types supported for this target type?
4. Queue / capacity / rate limits?

If any check fails → deny with a clear reason (feature disabled vs permission denied).

---

## Summary

- **Feature Flags** = system capability (global).
- **Permissions** = user/role capability (RBAC).
- **Target Types** = what is scanned (existing `TargetType` enum).
- **Scan Types** = which analyses run (separate from permissions).
- **Dangerous targets** (e.g. `local_mount`) = explicit list, default admin-only, optional security level for UI/policy.

This design keeps the model modular, avoids permission explosion, and aligns with patterns used in many security tools (e.g. Snyk, Trivy, Semgrep).
