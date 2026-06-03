# Finding policy and inline suppressions

Two **independent** channels — use either, or both:

| Channel | Needs `finding-policy.json`? | Best for |
|---------|-------------------------------|----------|
| **Inline comments** in source | **No** — always on by default | Single line / single finding |
| **`finding-policy.json`** | Yes (optional file) | Broad patterns (tests/**, same rule in many files) |

At report time SSC applies **inline first**, then JSON policy (if configured). Accepted findings show source `inline` or `policy`.

---

## Inline suppressions (no policy file)

Parsed from source under the scan target (`/app/target` in Docker). **No config file required** — put `# nosec` / `# nosemgrep` on the code and scan.

### Supported syntax

| Language | Example | Tools |
|----------|---------|--------|
| Python | `# nosec` / `# nosec B608 — parameterized via %s` | Bandit; cross-tool for CodeQL when id matches |
| Python | `# nosemgrep: python.lang.security.audit.sqli` | Semgrep; cross-tool when rule id matches |
| Python | `# ssc:accept py/sql-injection — values bound via %s` | Any SSC tool |
| Python | `# gitleaks:allow` | Gitleaks |
| JS/TS | `// eslint-disable-next-line no-eval` | ESLint (next line) |
| JS/TS | `// nosemgrep: rule-id` | Semgrep / cross-tool |

### Scope

- **Same line:** comment on the finding line applies.
- **Previous line:** `# nosec` / `# nosemgrep` on line N can cover line N+1 when N ends with `(`, `,`, `\`, etc. (multi-line call).
- **`eslint-disable-next-line`:** standard ESLint — applies to the following line.

```python
cur.execute(  # nosec B608  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query
    f"UPDATE t SET {', '.join(sets)} WHERE id = %s",
    args,
)
```

Bandit/Semgrep also honour native tags during the scan; SSC’s layer adds **cross-tool** acceptance (e.g. CodeQL) and report visibility.

### Optional tuning (environment only)

Not part of `finding-policy.json`.

| Variable | Default | Meaning |
|----------|---------|---------|
| `SSC_INLINE_SUPPRESSIONS_ENABLED` | on | Set `false` to disable |
| `SSC_INLINE_SUPPRESSIONS_LINE_LOOKBACK` | `1` | Lines above finding to check |
| `SSC_INLINE_SUPPRESSIONS_CROSS_TOOL_NOSEC` | on | `# nosec Bxxx` → non-Bandit tools |
| `SSC_INLINE_SUPPRESSIONS_CROSS_TOOL_NOSEMGREP` | on | `# nosemgrep` → non-Semgrep tools |

---

## JSON finding policy (optional)

For projects that want central, reviewable acceptances. Default path: `.scanning/finding-policy.json`

Schema: `GET /api/v1/finding-policy/schema` (per-tool `matchers` show which finding fields each regex uses). Validate before commit: `POST /api/v1/finding-policy/validate`. See [AGENT_API.md](AGENT_API.md#finding-policy-schema-for-false-positives).

Top-level keys must be **policy_key** values (e.g. `owasp_dc`, `npm_audit`), not UI labels like “OWASP Dependency Check”. Deprecated alias `owasp_dependency_check` is auto-mapped to `owasp_dc` at load time.

### Example

```json
{
  "semgrep": {
    "accepted_findings": [
      {
        "rule_id": "python.fastapi.security.wildcard-cors.wildcard-cors",
        "path_regex": ".*/backend/api/main\\.py$",
        "message_regex": "CORS policy allows any origin",
        "reason": "Intentional for dev; production restricts via reverse proxy."
      }
    ],
    "dedupe": {
      "enabled": true,
      "line_window": 2
    }
  }
}
```

### When to use which

| Situation | Prefer |
|-----------|--------|
| One-off FP on one `cur.execute(...)` | Inline on that line — **no policy file** |
| Same rule across many files / tests/** | `finding-policy.json` |
| Semgrep severity tweak for dev settings | Policy `severity_overrides` |

### Enabling the policy file for scans

Only if you use JSON policy:

- Commit `.scanning/finding-policy.json`
- Scan API / form: `finding_policy` path, or execution setting “apply by default”
- Docker: `FINDING_POLICY_FILE_IN_CONTAINER=/target/.scanning/finding-policy.json`

---

## Report and agents

- HTML report: **Accepted Findings** with source `inline` or `policy`.
- AI prompt: line FP → inline comment; broad FP → policy JSON.
- API schema documents inline syntax separately (`inline_suppression_syntax`, `inline_suppression_env`) — not as keys inside the policy file.
