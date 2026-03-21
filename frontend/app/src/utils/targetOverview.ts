import type { ScanTargetItem } from '../hooks/useTargets'

/** Last scan row is "done" enough for coverage / findings (not queue placeholders). */
export function isFinishedScanStatus(status: string | undefined | null): boolean {
  if (!status) return false
  const s = String(status).toLowerCase()
  return ['completed', 'failed', 'cancelled', 'interrupted'].includes(s)
}

export type TargetBucket = 'failed' | 'needs_attention' | 'clean' | 'other'

export function categorizeBucket(t: ScanTargetItem): TargetBucket {
  const ls = t.last_scan
  if (!ls) return 'other'
  const st = String(ls.status).toLowerCase()
  if (!isFinishedScanStatus(st)) return 'other'
  if (st === 'failed') return 'failed'
  const total = ls.total_vulnerabilities ?? 0
  if (total > 0) return 'needs_attention'
  return 'clean'
}

export type QuickPreset = 'all' | 'critical' | 'high' | 'clean' | 'failed'
export type SeverityFilter = '' | 'critical' | 'high' | 'medium' | 'low'
export type FindingsFilter = '' | 'has_findings' | 'clean' | 'failed_scan'
export type LastScanSort = 'risk' | 'recent' | 'oldest'

export function computeOverviewCounts(list: ScanTargetItem[]): {
  targetsWithCritical: number
  targetsWithHighOnly: number
  failed: number
  clean: number
} {
  let targetsWithCritical = 0
  let targetsWithHighOnly = 0
  let failed = 0
  let clean = 0

  for (const t of list) {
    const ls = t.last_scan
    if (!ls) continue
    const st = String(ls.status).toLowerCase()
    if (!isFinishedScanStatus(st)) continue
    if (st === 'failed') {
      failed++
      continue
    }
    const c = ls.critical_vulnerabilities ?? 0
    const h = ls.high_vulnerabilities ?? 0
    const total = ls.total_vulnerabilities ?? 0
    if (total === 0) {
      clean++
      continue
    }
    if (c > 0) targetsWithCritical++
    else if (h > 0) targetsWithHighOnly++
  }

  return { targetsWithCritical, targetsWithHighOnly, failed, clean }
}

function hasSeverityLevel(t: ScanTargetItem, level: SeverityFilter): boolean {
  if (!level) return true
  const ls = t.last_scan
  if (!ls || !isFinishedScanStatus(ls.status)) return false
  if (level === 'critical') return (ls.critical_vulnerabilities ?? 0) > 0
  if (level === 'high') return (ls.high_vulnerabilities ?? 0) > 0
  if (level === 'medium') return (ls.medium_vulnerabilities ?? 0) > 0
  if (level === 'low') return (ls.low_vulnerabilities ?? 0) > 0
  return true
}

function matchesFindingsFilter(t: ScanTargetItem, f: FindingsFilter): boolean {
  if (!f) return true
  const b = categorizeBucket(t)
  const total = t.last_scan?.total_vulnerabilities ?? 0
  if (f === 'failed_scan') return b === 'failed'
  if (f === 'clean') return b === 'clean'
  if (f === 'has_findings') return total > 0 && b !== 'clean'
  return true
}

/** Narrow list by severity + findings dropdowns (not quick preset). */
export function applyNarrowFilters(
  list: ScanTargetItem[],
  severityFilter: SeverityFilter,
  findingsFilter: FindingsFilter
): ScanTargetItem[] {
  return list.filter((t) => {
    if (!hasSeverityLevel(t, severityFilter)) return false
    return matchesFindingsFilter(t, findingsFilter)
  })
}

/** Apply overview quick preset on top of a list. */
export function applyQuickPreset(list: ScanTargetItem[], preset: QuickPreset): ScanTargetItem[] {
  if (preset === 'all') return list
  if (preset === 'critical') {
    return list.filter((t) => (t.last_scan?.critical_vulnerabilities ?? 0) > 0)
  }
  if (preset === 'high') {
    return list.filter((t) => {
      const ls = t.last_scan
      if (!ls) return false
      return (ls.high_vulnerabilities ?? 0) > 0 && (ls.critical_vulnerabilities ?? 0) === 0
    })
  }
  if (preset === 'clean') {
    return list.filter((t) => categorizeBucket(t) === 'clean')
  }
  if (preset === 'failed') {
    return list.filter((t) => categorizeBucket(t) === 'failed')
  }
  return list
}

/**
 * Sort key for risk-first display (higher = show first). UI-only; hook state stays API/SSE order.
 */
export function targetRiskSortKey(t: ScanTargetItem): { tier: number; score: number; id: string } {
  const ls = t.last_scan
  const id = String(t.id)
  if (!ls) return { tier: 0, score: 0, id }

  const st = String(ls.status).toLowerCase()
  if (!isFinishedScanStatus(st)) {
    return { tier: 1, score: 0, id }
  }

  const c = ls.critical_vulnerabilities ?? 0
  const h = ls.high_vulnerabilities ?? 0
  const m = ls.medium_vulnerabilities ?? 0
  const low = ls.low_vulnerabilities ?? 0
  const total = ls.total_vulnerabilities ?? 0

  const composite = c * 1_000_000 + h * 10_000 + m * 100 + low

  if (total > 0) {
    return { tier: 4, score: composite, id }
  }
  if (st === 'failed') {
    return { tier: 3, score: 0, id }
  }
  return { tier: 2, score: 0, id }
}

export function compareTargetsRiskFirst(a: ScanTargetItem, b: ScanTargetItem): number {
  const ka = targetRiskSortKey(a)
  const kb = targetRiskSortKey(b)
  if (ka.tier !== kb.tier) return kb.tier - ka.tier
  if (ka.score !== kb.score) return kb.score - ka.score
  return ka.id.localeCompare(kb.id)
}

export function sortByLastScanTime(list: ScanTargetItem[], order: 'recent' | 'oldest'): ScanTargetItem[] {
  const copy = [...list]
  copy.sort((a, b) => {
    const ta = a.last_scan?.completed_at ? new Date(a.last_scan.completed_at).getTime() : 0
    const tb = b.last_scan?.completed_at ? new Date(b.last_scan.completed_at).getTime() : 0
    return order === 'recent' ? tb - ta : ta - tb
  })
  return copy
}

export function sortVisibleTargets(
  list: ScanTargetItem[],
  lastScanSort: LastScanSort
): ScanTargetItem[] {
  if (lastScanSort === 'risk') {
    const copy = [...list]
    copy.sort(compareTargetsRiskFirst)
    return copy
  }
  return sortByLastScanTime(list, lastScanSort === 'recent' ? 'recent' : 'oldest')
}

export function formatRelativeScanTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const diff = Date.now() - d.getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 45) return 'just now'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m ago`
  const h = Math.floor(min / 60)
  if (h < 24) return `${h}h ago`
  const days = Math.floor(h / 24)
  if (days < 7) return `${days}d ago`
  return d.toLocaleDateString()
}

/** Highest severity label for icon/badge. */
export function topSeverityLabel(t: ScanTargetItem): 'critical' | 'high' | 'medium' | 'low' | 'none' {
  const ls = t.last_scan
  if (!ls) return 'none'
  if ((ls.critical_vulnerabilities ?? 0) > 0) return 'critical'
  if ((ls.high_vulnerabilities ?? 0) > 0) return 'high'
  if ((ls.medium_vulnerabilities ?? 0) > 0) return 'medium'
  if ((ls.low_vulnerabilities ?? 0) > 0) return 'low'
  return 'none'
}
