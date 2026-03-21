# Security fix flow — product roadmap

Informal planning for how **SimpleSecCheck** can help users go from **findings** to **fixed code**, without committing to a delivery date. Prioritize **Stage 1** before automation.

---

## Vision (one line)

**Scan → analysis → actionable fix guidance → (optional) PR / branch → rescan → done.**

The differentiator is not “another button,” but **structured context** (target, severity, findings, repo) that other tools often lack.

---

## Stage 1 — Fix intelligence layer *(do this first)*

**Goal:** No agents, no automatic repo write. Maximize developer productivity with **one great prompt** (and optional small UI).

**Example UX**

- Primary action: **Fix** (or **Fix this target**).
- Opens a **modal** with:
  - Severity + target summary
  - **Approach** (e.g. quick fix in Cursor/ChatGPT, PR-oriented wording, explain-only)
  - **Generated fix prompt** (copy-paste ready): repo URL, branch if known, bullet list of findings, goals (fix, preserve behavior, follow best practices)
  - Actions: **Copy**, **Open report**, optional **Open in editor** / deep-link where applicable

**Why it works**

- Teams already use Cursor, ChatGPT, Copilot, IDE agents. You become the **command center**: prioritization + context + a single place to start.

**Out of scope for Stage 1**

- Cloning repos, creating branches, or pushing commits on behalf of the user.

**Implemented (app):** My Targets **Fix** opens `FixTargetModal`, which loads the existing **`/api/results/{scanId}/ai-prompt`** response, prepends **approach** text (quick / PR-ready / explain), and offers **Copy** + **Open report**. Code: `frontend/app/src/components/FixTargetModal.tsx`, helpers in `frontend/app/src/utils/fixTargetPrompt.ts`.

---

## Stage 2 — Workflow integration *(low risk, high leverage)*

**Goal:** Connect guidance to **existing** Git hosting workflows without owning execution.

**Ideas**

- **Create fix PR** (assisted): generate branch name suggestion, PR title/body from the same prompt template, link to **“new PR”** or **new issue** on GitHub/GitLab (prefill where the host allows).
- **Exports:** `fix.md`, patch instructions, or issue body markdown.
- **Deep links:** open report with focus (e.g. severity / first critical) if the UI supports query params later.

**Still no** required write access to the user’s repository from SimpleSecCheck itself.

**Implemented (app):** `FixWorkflowPanel` inside **Fix this target** — suggested branch names, base/head branch fields, **download** `fix.md`, PR/issue templates, patch-workflow markdown, **copy** PR title/body, **open** GitHub “new issue” (prefilled) and **compare** (for PR after push), GitLab **new issue** / **new MR** when the target `source` parses as GitHub/GitLab. Code: `frontend/app/src/components/FixWorkflowPanel.tsx`, `frontend/app/src/utils/gitWorkflow.ts`, `frontend/app/src/utils/fixWorkflowTemplates.ts`.

---

## Stage 3 — Agent / hybrid mode *(product-level, later)*

**Goal:** Optional path from **prompt + context** to **branch / commits / PR**, with a human in the loop.

**Conceptual flow (hybrid)**

1. User approves scope (repo, branch, policy).
2. Worker or external API produces **branch + commits + PR** (or IDE agent uses the generated pack).
3. **GitHub Actions / CI** runs tests, lint, security gates — **tests are not “reimplemented” inside SimpleSecCheck**; the PR pipeline is the source of truth.
4. Optional: **rescan on PR** or on branch (webhook / `pull_request` → trigger scan for that ref).

**Reality check**

| Topic | Note |
|--------|------|
| Trust | Repo write is high risk; prefer **branch + PR + review** over silent auto-fix. |
| Quality | AI fixes can be wrong; CI + review mitigate. |
| Cost | Long-running agents have real cost; design as optional. |
| Debuggability | Need clear attribution: what changed, which finding, which run. |

**Non-goals for an initial Stage 3**

- “Fix everything automatically with no review.”
- Replacing CI with ad-hoc test runs inside the agent only.

**Implemented (guidance only, no backend agent):** Collapsible **Stage 3** block in the same modal — hybrid workflow text, **copy** local `git` commands, download **hybrid-workflow.md**, download an **example** GitHub Actions YAML (reminder job, not connected to your instance). Fully automated agents and **rescan-on-PR webhooks** remain future backend work.

**Implemented interface for external agents:**  
`POST /api/user/targets/{target_id}/agent-callback` (authenticated as the user) accepts agent metadata (`agent_name`, `branch_name`, `pr_url`, `commit_sha`, `trigger_rescan`) and can enqueue a scan immediately. For `git_repo` targets, `branch_name` is used as a **scan-time branch override** (target config is not permanently changed).

---

## Killer follow-up (when Stage 2/3 exist)

**Scan on the fix branch / PR**

- After a PR is opened (or updated), trigger a **scan for that ref**.
- Compare **before vs after** (e.g. critical count) — strong narrative for “did we actually improve?”

---

## Documentation hygiene

- **This file** is the single high-level reference for the fix journey.
- **Implementation** should be tracked in **issues/milestones** (Stage 1 tickets first).
- Update **ROADMAP.md** only with a pointer here if the high-level product direction changes.

---

## Related docs

- [ROADMAP.md](ROADMAP.md) — overall product direction
- [SCAN_RESULT_ACCESS.md](SCAN_RESULT_ACCESS.md) — how results/reports are exposed (relevant for “Open report”)
