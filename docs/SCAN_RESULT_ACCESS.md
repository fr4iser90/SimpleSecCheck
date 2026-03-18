# Scan results access

All access to **HTML reports** and **scan APIs** (detail, status, steps, aggregated results) is **owner-based**, with optional sharing.

## Owner

- **Logged-in:** `scans.user_id` = JWT user id.
- **Guest:** `scans.scan_metadata.session_id` = guest session cookie.

## Sharing (metadata JSON)

| Field | Purpose |
|-------|---------|
| `report_shared_with_user_ids` | List of user UUID strings — those users may **read** (GET scan, status, steps, report) like the owner. |
| `report_share_token` | Secret string (**≥ 8 chars**). Anyone with `GET /api/results/{scan_id}/report?share_token=...` can open the HTML report (link share). |

Owner sets these via **scan update** (metadata) or SQL.

### UI: copy share link

- **`POST /api/v1/scans/{scan_id}/report-share-link`** (owner only, JSON body optional: `{ "regenerate": false }`).
  - Creates a strong `report_share_token` if missing (or replaces it if `regenerate: true`).
  - Response: `{ "share_path": "/api/results/{scan_id}/report?share_token=..." }` — prepend your site origin for a full URL.
- **My Scans** (completed rows): **Copy share link** copies that full URL to the clipboard.
- **Scan view** (report embedded in app): **Copy share link** sits in the report toolbar next to Download CSV; it is **hidden** when the same HTML is opened as a **local file** (`file:`) or in a **standalone tab** (not inside the app iframe).

## Mutations (owner only)

Update scan metadata, delete scan, cancel, retry — **only the owner** (not shared users).

## List / recent scans

Only scans **you own** (by `user_id` or guest `session_id`).
