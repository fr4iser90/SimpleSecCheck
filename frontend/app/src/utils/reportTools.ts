/** Map scan steps to executed-tool rows (mirrors HTML report steps.log logic). */

const SETUP_STEP_PATTERN = /^(git clone|initialization|pre-scan|preparing|clone repository|setup)$/i

export type ToolDisplayStatus = 'complete' | 'failed' | 'skipped' | 'running'

export interface ExecutedTool {
  name: string
  status: ToolDisplayStatus
  message: string
}

export interface ScanStepLike {
  name?: string
  status?: string
  message?: string
}

export function stepsToExecutedTools(steps: ScanStepLike[]): ExecutedTool[] {
  const byName = new Map<string, ExecutedTool>()
  for (const step of steps) {
    const name = (step.name ?? '').trim()
    if (!name || SETUP_STEP_PATTERN.test(name)) continue

    const msg = step.message ?? ''
    let status: ToolDisplayStatus = 'complete'
    if (step.status === 'failed') {
      status = 'failed'
    } else if (step.status === 'running') {
      status = 'running'
    } else if (step.status === 'completed') {
      status = /skipping|\bskip\b/i.test(msg) ? 'skipped' : 'complete'
    } else if (step.status === 'pending') {
      continue
    }

    byName.set(name, { name, status, message: msg })
  }
  return Array.from(byName.values()).sort((a, b) => a.name.localeCompare(b.name))
}

export function toolsProgress(tools: ExecutedTool[]): { total: number; passed: number } {
  return {
    total: tools.length,
    passed: tools.filter((t) => t.status === 'complete').length,
  }
}

export function overallStatusFromCounts(
  critical: number,
  high: number,
): 'Critical' | 'High' | 'OK' {
  if (critical > 0) return 'Critical'
  if (high > 0) return 'High'
  return 'OK'
}

export function resolveFindingPolicyPath(metadata: Record<string, unknown> | undefined): string | null {
  if (!metadata) return null
  const raw = metadata.finding_policy_path ?? metadata.finding_policy
  if (typeof raw === 'string' && raw.trim()) {
    return raw.replace(/^\/target\//, '')
  }
  if (metadata.finding_policy_default_applied === true) {
    return '.scanning/finding-policy.json'
  }
  return null
}

export function formatReportTimestamp(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
