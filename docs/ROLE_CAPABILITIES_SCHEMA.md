# Role Capabilities Schema

Role capabilities configure, per role (guest, user, admin), which target types and scanners are allowed and whether **My Targets** is enabled. This is stored in `SystemState.config["role_capabilities"]` and exposed via:

- **GET** `/api/admin/config/role-capabilities` — read (admin only)
- **PUT** `/api/admin/config/role-capabilities` — update (admin only)

Feature flags (e.g. `ALLOW_GIT_REPOS`) remain the **global** switch for “does the instance support this target type?”. Role capabilities then **restrict by role** which of those enabled types (and which scanners) each role may use.

---

## JSON structure in `config["role_capabilities"]`

```json
{
  "guest": {
    "allowed_target_types": ["git_repo", "uploaded_code"],
    "allowed_scanner_tools_keys": [],
    "my_targets_allowed": false,
    "my_targets_target_types": null
  },
  "user": {
    "allowed_target_types": ["git_repo", "uploaded_code", "container_registry", "website", "api_endpoint", "network_host", "kubernetes_cluster", "apk", "ipa", "openapi_spec", "local_mount"],
    "allowed_scanner_tools_keys": [],
    "my_targets_allowed": true,
    "my_targets_target_types": null
  },
  "admin": {
    "allowed_target_types": ["git_repo", "uploaded_code", "container_registry", "website", "api_endpoint", "network_host", "kubernetes_cluster", "apk", "ipa", "openapi_spec", "local_mount"],
    "allowed_scanner_tools_keys": [],
    "my_targets_allowed": true,
    "my_targets_target_types": null
  }
}
```

---

## Field reference (per role)

| Field | Type | Meaning |
|-------|------|--------|
| `allowed_target_types` | `string[]` | Backend target type keys this role may use for scans. Must be a subset of the valid set (see below). **Empty** = role may not use any of these target types. |
| `allowed_scanner_tools_keys` | `string[]` | Scanner slugs (e.g. `semgrep`, `trivy`, `sonarqube`) this role may use. **Empty** = no restriction (all scanners allowed). Non-empty = only these scanners. |
| `my_targets_allowed` | `boolean` | Whether this role may use My Targets (create/list/update/delete own targets). Typically `false` for guest, `true` for user and admin. |
| `my_targets_target_types` | `string[]` or `null` | If set, My Targets is restricted to these target types only. If `null`, the same as `allowed_target_types` for My Targets. |

---

## Valid `allowed_target_types` / `my_targets_target_types` values

These must match the backend target type enum / `TARGET_PERMISSION_MAP` in `domain/services/target_permission_policy.py`:

- `git_repo`
- `uploaded_code` (ZIP upload)
- `local_mount` (local paths)
- `container_registry`
- `website`
- `api_endpoint`
- `network_host`
- `kubernetes_cluster`
- `apk`
- `ipa`
- `openapi_spec`

Validation on PUT returns `400` if an invalid type is sent; the error message lists the valid set.

---

## Scanner keys (`allowed_scanner_tools_keys`)

Use the **tools_key** (slug) from the scanner manifest / DB (e.g. `semgrep`, `trivy`, `sonarqube`, `snyk`). These are the same keys used in `/api/admin/scanner-tool-settings`. No validation against the current scanner list is done on PUT; unknown keys simply result in “no scanners allowed” when enforcing.

---

## Defaults when no config is stored

If `config["role_capabilities"]` is missing or a role key is missing, the API and enforcement use:

- **guest:** `allowed_target_types`: `["git_repo", "uploaded_code"]`, `my_targets_allowed`: `false`, `allowed_scanner_tools_keys`: `[]` (all scanners).
- **user:** all valid target types, `my_targets_allowed`: `true`, `allowed_scanner_tools_keys`: `[]`.
- **admin:** same as user (all targets, My Targets, all scanners).

---

## Relation to feature flags

- **Feature flags** (e.g. in Admin → Feature Flags): “Is this target type / feature enabled for the **instance**?”
- **Role capabilities**: “For this **role**, which of those enabled target types and scanners are allowed, and is My Targets allowed?”

Effective allowed target types for a role = intersection of (feature-flag enabled types) and `role_capabilities[role].allowed_target_types`. The frontend config API should expose this intersection (and `my_targets_allowed`) so the UI can hide/disable options accordingly.

---

## Pydantic models (API)

- **Response / stored shape:** `RoleCapabilitiesResponse` with `guest`, `user`, `admin` of type `RoleCapabilityEntry`.
- **PUT body:** `RoleCapabilitiesRequest` with optional `guest`, `user`, `admin`. Only provided roles are updated; others are left unchanged.
- **Per-role:** `RoleCapabilityEntry`: `allowed_target_types`, `allowed_scanner_tools_keys`, `my_targets_allowed`, `my_targets_target_types`.

See `backend/api/routes/admin.py` for the exact field types and validation.
