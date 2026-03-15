export interface GitHubRepo {
  id: string
  repo_url: string
  repo_owner: string | null
  repo_name: string
  branch: string
  auto_scan_enabled: boolean
  scan_on_push: boolean
  scan_frequency: string
  created_at: string
  updated_at: string
  last_scan: {
    scan_id: string | null
    score: number
    vulnerabilities: { critical: number, high: number, medium: number, low: number }
    created_at: string
  } | null
  score: number | null
  vulnerabilities: { critical: number, high: number, medium: number, low: number } | null
}

export interface RepoScanStatus {
  has_active_scan: boolean
  status: string | null
  scan_id: string | null
  queue_position: number | null
  created_at?: string
}

export type FilterType = 'all' | 'healthy' | 'needs_attention' | 'critical' | 'not_scanned'
export type SortType = 'name' | 'score' | 'last_scan' | 'vulnerabilities'

export type RepoStatus = {
  type: 'healthy' | 'needs_attention' | 'critical' | 'not_scanned' | 'queued' | 'scanning'
  label: string
  color: string
}

export const getScoreColor = (score: number | null): string => {
  if (!score) return 'var(--text-secondary)'
  if (score >= 80) return 'var(--color-pass)'
  if (score >= 60) return 'var(--color-medium)'
  return 'var(--color-critical)'
}

export const getVulnCount = (repo: GitHubRepo): number => {
  if (!repo.vulnerabilities) return 0
  return (repo.vulnerabilities.critical || 0) + 
         (repo.vulnerabilities.high || 0) + 
         (repo.vulnerabilities.medium || 0) + 
         (repo.vulnerabilities.low || 0)
}

export const getRepoStatus = (repo: GitHubRepo, scanStatus?: RepoScanStatus): RepoStatus => {
  // Check if scan is active
  if (scanStatus?.has_active_scan) {
    if (scanStatus.status === 'running') {
      return { type: 'scanning', label: 'Scanning', color: 'var(--accent)' }
    }
    if (scanStatus.status === 'pending') {
      return { type: 'queued', label: 'Queued', color: 'var(--color-medium)' }
    }
  }
  
  // Check if never scanned
  if (!repo.score && !repo.last_scan) {
    return { type: 'not_scanned', label: 'Not Scanned', color: 'var(--text-secondary)' }
  }
  
  const score = repo.score || 0
  const vulns = repo.vulnerabilities || { critical: 0, high: 0, medium: 0, low: 0 }
  
  // Critical: score < 60 or has critical vulnerabilities
  if (score < 60 || vulns.critical > 0) {
    return { type: 'critical', label: 'Critical', color: 'var(--color-critical)' }
  }
  
  // Needs attention: score 60-79 or has high vulnerabilities
  if (score < 80 || vulns.high > 0) {
    return { type: 'needs_attention', label: 'Needs Attention', color: 'var(--color-medium)' }
  }
  
  // Healthy: score >= 80 and no critical/high vulnerabilities
  return { type: 'healthy', label: 'Healthy', color: 'var(--color-pass)' }
}

export const getDaysSinceLastScan = (repo: GitHubRepo): number | null => {
  if (!repo.last_scan) return null
  const lastScanDate = new Date(repo.last_scan.created_at)
  const now = new Date()
  const diffTime = Math.abs(now.getTime() - lastScanDate.getTime())
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return diffDays
}

export const getWarnings = (repo: GitHubRepo, scanStatus?: RepoScanStatus): string[] => {
  const warnings: string[] = []
  const vulns = repo.vulnerabilities || { critical: 0, high: 0, medium: 0, low: 0 }
  const daysSince = getDaysSinceLastScan(repo)
  
  if (vulns.critical > 0) {
    warnings.push(`⚠️ This repository has ${vulns.critical} critical vulnerability${vulns.critical > 1 ? 'ies' : ''} that need immediate attention`)
  }
  
  if (daysSince !== null && daysSince > 7) {
    warnings.push(`⏰ Last scan was ${daysSince} days ago - consider running a new scan`)
  }
  
  if (scanStatus?.has_active_scan && scanStatus.status === 'pending' && scanStatus.queue_position) {
    warnings.push(`🔄 Scan is currently in queue (position #${scanStatus.queue_position})`)
  }
  
  return warnings
}

export const calculateStats = (repos: GitHubRepo[], getRepoStatusFn: (repo: GitHubRepo) => RepoStatus) => {
  const total = repos.length
  const scanned = repos.filter(r => r.score !== null || r.last_scan !== null).length
  const needsAttention = repos.filter(r => {
    const status = getRepoStatusFn(r)
    return status.type === 'needs_attention' || status.type === 'critical'
  }).length
  const critical = repos.filter(r => {
    const status = getRepoStatusFn(r)
    return status.type === 'critical'
  }).length
  
  return { total, scanned, needsAttention, critical }
}
