import { Link } from 'react-router-dom'
import type { ScanTargetItem } from '../hooks/useTargets'
import { formatRelativeScanTime, topSeverityLabel } from '../utils/targetOverview'

const DOT: Record<string, string> = {
  critical: '🔴',
  high: '🟠',
  medium: '🟡',
  low: '🟡',
  none: '⚪',
}

interface TargetSectionRowProps {
  target: ScanTargetItem
  variant: 'needs_attention' | 'failed'
  onScanNow: (targetId: string) => void
  scanLoading?: boolean
}

export default function TargetSectionRow({
  target,
  variant,
  onScanNow,
  scanLoading,
}: TargetSectionRowProps) {
  const label = target.display_name || target.source
  const ls = target.last_scan
  const top = topSeverityLabel(target)
  const reportLink =
    ls && (ls.status === 'completed' || ls.status === 'failed')
      ? `/api/results/${ls.scan_id}/report`
      : null

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'flex-start',
        gap: '0.75rem',
        padding: '0.75rem 1rem',
        borderRadius: '8px',
        border: '1px solid var(--glass-border-main)',
        background: 'var(--glass-bg-main)',
      }}
    >
      <div style={{ fontSize: '1.1rem', lineHeight: 1.2, flexShrink: 0 }}>{DOT[top] ?? DOT.none}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, marginBottom: '0.25rem', wordBreak: 'break-word' }}>
          {label.length > 70 ? label.slice(0, 70) + '…' : label}
        </div>
        {variant === 'failed' && (
          <div style={{ fontSize: '0.85rem', color: 'var(--color-warning, #fd7e14)', marginBottom: '0.35rem' }}>
            Last scan failed
          </div>
        )}
        {ls && ls.total_vulnerabilities > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
            {ls.critical_vulnerabilities > 0 && (
              <span style={{ color: 'var(--color-critical, #dc3545)' }}>{ls.critical_vulnerabilities} critical</span>
            )}
            {ls.high_vulnerabilities > 0 && (
              <span style={{ color: 'var(--color-warning, #fd7e14)' }}>{ls.high_vulnerabilities} high</span>
            )}
            {ls.medium_vulnerabilities > 0 && (
              <span style={{ color: 'var(--color-info, #0dcaf0)' }}>{ls.medium_vulnerabilities} medium</span>
            )}
            {ls.low_vulnerabilities > 0 && (
              <span style={{ color: 'var(--text-secondary)' }}>{ls.low_vulnerabilities} low</span>
            )}
          </div>
        )}
        {ls?.completed_at && (
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Last scan: {formatRelativeScanTime(ls.completed_at)}
          </div>
        )}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
        {reportLink && (
          <Link to={reportLink} style={{ fontSize: '0.85rem', color: 'var(--accent, #0d6efd)', fontWeight: 500 }}>
            View
          </Link>
        )}
        {reportLink && (
          <Link to={reportLink} style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Fix
          </Link>
        )}
        <button
          type="button"
          className="primary"
          style={{ fontSize: '0.8rem', padding: '0.25rem 0.6rem' }}
          onClick={() => onScanNow(target.id)}
          disabled={scanLoading}
        >
          {scanLoading ? '…' : 'Rescan'}
        </button>
      </div>
    </div>
  )
}
