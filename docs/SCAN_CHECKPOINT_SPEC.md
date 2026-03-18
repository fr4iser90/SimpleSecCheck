# Scan checkpoint & resume — internal spec

**Status:** implemented (scanner-side); optional per-plugin via manifest  
**Audience:** backend/scanner/worker maintainers  

This document defines how interrupted scans may resume safely. **File on volume is source of truth; DB is cache/mirror only.**

---

## 1. Goals

- After crash / `docker compose down` / worker restart, avoid re-running steps that are **provably complete** under the **same** scan configuration and target revision.
- **Never** resume on stale or ambiguous artifacts (wrong tool version, changed flags, corrupt file).

---

## 2. Storage

| Location | Role |
|----------|------|
| `results/{scan_id}/logs/checkpoint.json` | **Source of truth** — scanner reads/writes |
| DB column (optional, future) | Mirror for UI/API — **never** sole authority |

---

## 3. Top-level schema (`checkpoint.json`)

```json
{
  "version": 1,
  "status": "running | resumed | completed",
  "resumed": false,
  "scan_config_hash": "<sha256>",
  "target_fingerprint": "<e.g. git commit SHA after clone>",
  "steps": {},
  "pipeline_order": ["git_clone", "init", "metadata", "semgrep", "trivy"]
}
```

| Field | Definition |
|-------|------------|
| `version` | Schema version; bump when structure or semantics change. |
| `status` | `running` — scan in progress; `resumed` — at least one step was skipped from checkpoint (see §6); `completed` — full pipeline finished successfully. |
| `resumed` | **Derived rule:** `true` iff any step in `steps` has `status == "skipped"` **and** that skip was due to checkpoint replay (not user “skip scanner”). Implementation may set explicitly at end of “skip pass”. |
| `scan_config_hash` | See §4. |
| `target_fingerprint` | Immutable id of scanned tree after clone (e.g. `git rev-parse HEAD`). Mismatch → invalidate checkpoint or full rescan. |
| `steps` | Map keyed by stable step id (see §5). |
| `pipeline_order` | **Explicit ordered list** of pipeline phases. Resume must not skip step N if step N−1 is not completed-or-skipped-valid. Order is fixed in code; this field is optional mirror for debugging. |

---

## 4. `config_hash` (per step)

**Definition:** single SHA-256 over a **canonical JSON** blob (sorted keys, UTF-8) built from:

1. **Scanner CLI flags / options** actually passed to the tool for this run.
2. **Relevant manifest fields** for that scanner (from `manifest.yaml`: enabled scanners slice, timeouts, scanner-specific options exposed to orchestrator).
3. **Effective env overrides** merged for that scanner (`SCANNER_TOOL_OVERRIDES_JSON` + any step-relevant env).

**Not included:** secrets (tokens); use a placeholder key name only if presence/absence changes behavior (e.g. `SNYK_TOKEN_set: true/false`).

**Rule:** If stored `config_hash` ≠ newly computed hash → **do not skip**; re-run step.

---

## 5. Step object (`steps.<step_id>`)

**Step id:** stable lowercase key, e.g. `git_clone`, `init`, `metadata`, `semgrep`, `trivy`, `codeql`, … (align with orchestrator / registry).

```json
{
  "status": "pending | running | completed | failed | skipped",
  "completed_at": "ISO8601 | null",
  "tool_version": "string | null",
  "config_hash": "sha256…",
  "artifact_hash": "sha256… | null",
  "skip_reason": "string | null"
}
```

| `status` | Meaning |
|----------|---------|
| `pending` | Not started or invalidated. |
| `running` | In progress (optional; helps crash diagnosis). |
| `completed` | Finished successfully; artifacts validated. |
| `failed` | Step ran and failed; **do not** skip on resume unless operator clears checkpoint. |
| `skipped` | Not executed this run: e.g. replay from checkpoint, or intentional skip (document in `skip_reason`). |

---

## 6. `resumed` flag — when exactly?

Set **`resumed: true`** when **any** step was executed as **checkpoint skip** (same as: would have run but was omitted because prior run’s `completed` + hashes + artifact checks passed).

Do **not** set solely because scan was re-queued after `running → pending`; only when replay actually skipped work.

---

## 7. `artifact_hash`

**Definition:** `sha256` of the **single primary output file** for that step (binary read, hash whole file).

- **Do not** hash directories or arbitrary globs (slow, non-deterministic).
- **Examples (illustrative — confirm paths in code):**

| Step id | Primary file for hash |
|---------|------------------------|
| `semgrep` | e.g. `tools/semgrep/report.json` |
| `trivy` | e.g. `tools/trivy/report.json` (or agreed canonical JSON) |
| `codeql` | e.g. per-language SARIF used as source of truth |
| … | Each scanner documents one path in manifest or shared table |

On resume: recompute hash of that file; must match stored `artifact_hash` **and** pass validation (§8).

---

## 8. Artifact validation (order: cheap → expensive)

Before treating a step as resumable:

1. Path exists.
2. `size > 0`.
3. **Parse** — e.g. `json.loads` for JSON; minimal SARIF structure check where applicable.
4. Compare **`artifact_hash`** to stored value.

If any check fails → drop `completed` for that step (or entire checkpoint if global corruption) and **re-run**.

---

## 9. Skip rule (hard)

Skip execution of step **S** only if **all** hold:

1. `scan_config_hash` (global) matches current run.
2. `target_fingerprint` matches current target after clone.
3. All steps **before S** in **pipeline order** are `completed` or valid `skipped` (checkpoint).
4. `steps[S].status == "completed"`.
5. `steps[S].tool_version` matches current tool `--version` (or equivalent).
6. `steps[S].config_hash` matches newly computed config hash.
7. Artifact validation (§8) passes; hash matches `artifact_hash`.

Otherwise → run **S** (possibly clearing stale step state).

---

## 10. Git clone

**Enterprise default:** **always clone** fresh into `/target` on each container run.  
Optional future: `reuse_workspace: true` with explicit commit verification — not default.

---

## 11. CodeQL (multi-phase)

Track sub-state per language, e.g.:

```json
"codeql": {
  "status": "completed",
  "python": { "db_ready": true, "analyze_done": true },
  "javascript": { "db_ready": true, "analyze_done": false }
}
```

- If `db_ready && !analyze_done` → run **analyze only** (do not recreate DB unless DB dir invalid).
- Half-created DB → treat as failed; recreate DB for that language.

`artifact_hash` applies to the **primary SARIF** (or agreed output) after analyze.

---

## 12. Orchestrator vs backend

| Component | Responsibility |
|-----------|----------------|
| Backend / queue | Enqueue scan; `running → pending` on recovery. |
| Scanner orchestrator | Load/validate checkpoint; decide skip/run; write checkpoint. |

---

## 13. Implementation phases (reference)

1. `checkpoint.json` I/O + `version` + global hashes.
2. Fixed **pipeline order** in code; per-step `config_hash` / `tool_version` / strict artifact checks for 1–2 scanners.
3. Extend to all scanners; CodeQL phased state.
4. Optional DB mirror + UI banner when `resumed === true`.

---

## 14. Plugin manifest (`checkpoint`)

**Plug-and-play:** Only plugins that declare a `checkpoint` block participate in resume. Others always execute.

**Plugins with checkpoint** (when primary artifact exists + hashes match):  
android, anchore, bandit, brakeman, burp, checkov, clair, codeql, detect_secrets, docker_bench, eslint, gitleaks, ios, ios_plist, kube_bench, kube_hunter, nikto, nuclei, npm_audit, owasp, safety, semgrep, snyk, sonarqube, terraform, trufflehog, trivy, wapiti, zap (`report.xml`, format `any`).  
Excluded: `base`, `test` (non-scanners).

```yaml
# scanner/plugins/<id>/manifest.yaml
checkpoint:
  primary_artifact: report.json   # relative to results/<scan_id>/tools/<id>/
  artifact_format: json          # json | sarif | any
  version_command: [trivy, version]   # optional; if omitted, tool_version not enforced
```

Orchestrator stores steps under keys `scanner:<manifest.id>` (same as `tools_key`).  
Disable all resume: env `SCAN_CHECKPOINT_DISABLE=1`.  
Resume requires a **git** target fingerprint (`git rev-parse HEAD`); local mounts without `.git` clear scanner checkpoints.

**Git in Docker:** Orchestrator calls `git config --global safe.directory` for the clone path (and `*`) so `rev-parse` / Semgrep are not blocked by “dubious ownership”. Optional **`GIT_CLONE_FULL=1`** on the worker (forwarded to the scan container) uses a non-shallow clone if shallow clones break `git ls-files` / Semgrep.

## 15. Changelog

| Date | Change |
|------|--------|
| 2026-03-18 | Initial enterprise spec (steps map, statuses, hashes, order, CodeQL, resumed rule). |
| 2026-03-18 | Implementation: `scanner/core/scan_checkpoint.py`, orchestrator integration, manifest `checkpoint` on major plugins. |
| 2026-03-18 | `safe.directory` + optional `GIT_CLONE_FULL`; no `upstream_rerun` gate; checkpoint steps only when fingerprint OK. |
| 2026-03-18 | Checkpoint added for CodeQL, OWASP, Snyk, SonarQube manifests; SonarQube `report.json` on skip/success. |
| 2026-03-18 | Checkpoint on remaining plugins: android, anchore, burp, clair, docker_bench, ios, ios_plist, kube_bench, kube_hunter, nikto, nuclei, wapiti, zap. |
