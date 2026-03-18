# Scan enforcement (rate limits & policies)

Configured in **Admin → Execution** (`execution_limits`) and **Admin → Security policies** (`policies`). Stored in `SystemState.config`.

## Execution limits

| Field | Effect |
|-------|--------|
| `max_scans_per_hour_global` | All new scans in the last rolling hour (DB `created_at`). |
| `max_scans_per_hour_per_user` | Per authenticated `user_id`. |
| `max_scans_per_hour_per_guest_session` | Per guest; uses `scan_metadata.session_id`. |
| `max_concurrent_scans_per_user` | Count of scans in `pending` or `running` per user. |
| `max_concurrent_scans_per_guest` | Same for guest session. |
| `rate_limit_admins` | If `true`, admins are subject to hourly/concurrent limits too. |
| `max_scan_duration_seconds` | Worker wall-clock wait for the scanner container (300–86400). Sent on the queue payload as `max_scan_wall_seconds`. |

Scan **retry** re-runs policy checks only (not hourly/concurrent limits).

## Policies

| Field | Effect |
|-------|--------|
| `blocked_target_patterns` | List of globs against `target_url`, or `regex:<pattern>`. |
| `blocked_scan_types` | Lowercase scan types (`code`, `container`, …) rejected with 403. |
| `require_auth_for_git` | If true, `target_type` `git_repo` requires a logged-in user. |

API: `GET/PUT /api/admin/config/scan-enforcement`.
