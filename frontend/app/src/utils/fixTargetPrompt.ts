import type { ScanTargetItem } from '../hooks/useTargets'

export type FixApproach = 'quick' | 'pr_ready' | 'explain'

/** Human-readable top severity for the modal header. */
export function formatTopSeverityLabel(t: ScanTargetItem): string {
  const ls = t.last_scan
  if (!ls || ls.total_vulnerabilities <= 0) {
    const st = ls ? String(ls.status).toLowerCase() : ''
    if (st === 'failed') return 'Failed scan (see report)'
    return 'None'
  }
  if (ls.critical_vulnerabilities > 0) return 'Critical'
  if (ls.high_vulnerabilities > 0) return 'High'
  if (ls.medium_vulnerabilities > 0) return 'Medium'
  if (ls.low_vulnerabilities > 0) return 'Low'
  return 'Unknown'
}

function findingsSummary(t: ScanTargetItem): string {
  const ls = t.last_scan
  if (!ls) return 'No scan summary available.'
  const parts: string[] = []
  if (ls.critical_vulnerabilities > 0) parts.push(`${ls.critical_vulnerabilities} critical`)
  if (ls.high_vulnerabilities > 0) parts.push(`${ls.high_vulnerabilities} high`)
  if (ls.medium_vulnerabilities > 0) parts.push(`${ls.medium_vulnerabilities} medium`)
  if (ls.low_vulnerabilities > 0) parts.push(`${ls.low_vulnerabilities} low`)
  if (parts.length === 0) return `Last scan status: ${ls.status}. Total findings (aggregated): ${ls.total_vulnerabilities}.`
  return parts.join(', ')
}

function targetMeta(t: ScanTargetItem): string {
  const lines = [`Display name: ${t.display_name || '(none)'}`, `Source / URL: ${t.source}`, `Type: ${t.type}`]
  const branch = t.config?.branch
  if (branch != null) lines.push(`Branch: ${String(branch)}`)
  if (t.scanners?.length) lines.push(`Scanners used: ${t.scanners.join(', ')}`)
  return lines.join('\n')
}

/**
 * Instructions prepended before the backend-generated finding prompt (per roadmap Stage 1).
 */
export function buildApproachPreamble(approach: FixApproach, target: ScanTargetItem): string {
  const label = target.display_name || target.source
  const summary = findingsSummary(target)
  const meta = targetMeta(target)

  const base = `## SimpleSecCheck — fix context\n\n**Target:** ${label}\n**Top severity:** ${formatTopSeverityLabel(target)}\n**Findings (counts):** ${summary}\n\n### Target metadata\n${meta}\n`

  const tail = {
    quick: `\n### Approach: Quick fix (IDE / chat)\nUse Cursor, VS Code Copilot, ChatGPT, or your usual assistant. Apply **small, reviewable** changes. Prefer fixing highest severity first. Do not weaken security for convenience.\n`,
    pr_ready: `\n### Approach: PR-ready patch\nProduce changes suitable for a **pull request**: logical commits, clear rationale, update tests if present, note breaking changes. The detailed finding list follows.\n`,
    explain: `\n### Approach: Explain only\nExplain **root causes**, **risk**, and **remediation options** before changing code. No obligation to produce a full patch in one shot.\n`,
  }

  return base + tail[approach]
}

/** Combine approach preamble, separator, and remote prompt from /ai-prompt API. */
export function combineFixPrompt(preamble: string, remotePrompt: string): string {
  return `${preamble.trim()}\n\n---\n\n## Findings detail (generated prompt)\n\n${remotePrompt.trim()}`
}
