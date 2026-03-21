import { Link } from 'react-router-dom'
import type { ScanTargetItem } from '../hooks/useTargets'
import { TARGET_TYPE_LABELS } from './TargetCard'
import { formatRelativeScanTime, topSeverityLabel } from '../utils/targetOverview'

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--color-critical, #dc3545)',
  high: 'var(--color-warning, #fd7e14)',
  medium: 'var(--color-info, #0dcaf0)',
  low: 'var(--text-secondary)',
  none: 'var(--text-secondary)',
}

interface MyTargetsTableProps {
  targets: ScanTargetItem[]
  onScanNow: (targetId: string) => void
  onEdit: (target: ScanTargetItem) => void
  scanLoadingId: string | null
  selectedIds: Set<string>
  onToggleSelect: (targetId: string) => void
}

export default function MyTargetsTable({
  targets,
  onScanNow,
  onEdit,
  scanLoadingId,
  selectedIds,
  onToggleSelect,
}: MyTargetsTableProps) {
  return (
    <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid var(--glass-border-main)' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
        <thead>
          <tr style={{ background: 'var(--glass-border-main)', textAlign: 'left' }}>
            <th style={{ padding: '0.6rem 0.75rem', width: '2rem' }} aria-label="Select" />
            <th style={{ padding: '0.6rem 0.75rem' }}>Target</th>
            <th style={{ padding: '0.6rem 0.75rem' }}>Type</th>
            <th style={{ padding: '0.6rem 0.75rem' }}>Findings</th>
            <th style={{ padding: '0.6rem 0.75rem' }}>Last scan</th>
            <th style={{ padding: '0.6rem 0.75rem' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {targets.map((t) => {
            const label = t.display_name || t.source
            const ls = t.last_scan
            const top = topSeverityLabel(t)
            const reportLink =
              ls && (ls.status === 'completed' || ls.status === 'failed')
                ? `/api/results/${ls.scan_id}/report`
                : null
            return (
              <tr key={t.id} style={{ borderTop: '1px solid var(--glass-border-main)' }}>
                <td style={{ padding: '0.5rem 0.75rem', verticalAlign: 'middle' }}>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(t.id)}
                    onChange={() => onToggleSelect(t.id)}
                    aria-label={`Select ${label}`}
                    style={{ width: '1.1rem', height: '1.1rem', cursor: 'pointer' }}
                  />
                </td>
                <td style={{ padding: '0.5rem 0.75rem', verticalAlign: 'middle', maxWidth: '280px' }}>
                  <div style={{ fontWeight: 600, wordBreak: 'break-word' }}>
                    {label.length > 48 ? label.slice(0, 48) + '…' : label}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>
                    {t.source}
                  </div>
                </td>
                <td style={{ padding: '0.5rem 0.75rem', verticalAlign: 'middle', whiteSpace: 'nowrap' }}>
                  {TARGET_TYPE_LABELS[t.type] || t.type}
                </td>
                <td style={{ padding: '0.5rem 0.75rem', verticalAlign: 'middle' }}>
                  {ls ? (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', alignItems: 'center' }}>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '0.12rem 0.4rem',
                          borderRadius: '6px',
                          border: `1px solid ${SEV_COLOR[top]}`,
                          color: SEV_COLOR[top],
                        }}
                      >
                        {top === 'none' ? ls.status : top}
                      </span>
                      {ls.total_vulnerabilities > 0 && (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                          {ls.critical_vulnerabilities > 0 && (
                            <span style={{ color: SEV_COLOR.critical }}>{ls.critical_vulnerabilities} C </span>
                          )}
                          {ls.high_vulnerabilities > 0 && (
                            <span style={{ color: SEV_COLOR.high }}>{ls.high_vulnerabilities} H </span>
                          )}
                          {ls.medium_vulnerabilities > 0 && (
                            <span style={{ color: SEV_COLOR.medium }}>{ls.medium_vulnerabilities} M </span>
                          )}
                          {ls.low_vulnerabilities > 0 && <span>{ls.low_vulnerabilities} L</span>}
                        </span>
                      )}
                    </div>
                  ) : (
                    <span style={{ color: 'var(--text-secondary)' }}>—</span>
                  )}
                </td>
                <td style={{ padding: '0.5rem 0.75rem', verticalAlign: 'middle', whiteSpace: 'nowrap' }}>
                  {ls ? (
                    <>
                      <div>{formatRelativeScanTime(ls.completed_at)}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{ls.status}</div>
                    </>
                  ) : (
                    '—'
                  )}
                </td>
                <td style={{ padding: '0.5rem 0.75rem', verticalAlign: 'middle' }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                    {reportLink && (
                      <Link to={reportLink} style={{ fontSize: '0.85rem', color: 'var(--accent, #0d6efd)' }}>
                        View
                      </Link>
                    )}
                    <button
                      type="button"
                      className="primary"
                      style={{ fontSize: '0.8rem', padding: '0.2rem 0.5rem' }}
                      onClick={() => onScanNow(t.id)}
                      disabled={scanLoadingId === t.id}
                    >
                      {scanLoadingId === t.id ? '…' : 'Rescan'}
                    </button>
                    <button type="button" style={{ fontSize: '0.8rem', padding: '0.2rem 0.5rem' }} onClick={() => onEdit(t)}>
                      Edit
                    </button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
