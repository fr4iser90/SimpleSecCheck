import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import type { ActiveScanSummary, ScanTargetItem } from '../hooks/useTargets'

/** Labels for target `type` (filters, badges). */
export const TARGET_TYPE_LABELS: Record<string, string> = {
  git_repo: 'Git repo',
  container_registry: 'Container',
  local_mount: 'Local path',
  website: 'Website',
  api_endpoint: 'API',
  network_host: 'Network',
  uploaded_code: 'ZIP upload',
  kubernetes_cluster: 'Kubernetes',
  apk: 'APK',
  ipa: 'IPA',
  openapi_spec: 'OpenAPI',
}

const TYPE_ICONS: Record<string, string> = {
  git_repo: '📦',
  container_registry: '🐳',
  local_mount: '📁',
  website: '🌐',
  api_endpoint: '🔌',
  network_host: '🖧',
  uploaded_code: '📎',
  kubernetes_cluster: '☸️',
  apk: '📱',
  ipa: '📱',
  openapi_spec: '📄',
}

interface TargetCardProps {
  target: ScanTargetItem
  initialScanDelaySeconds?: number
  onScanNow: (targetId: string) => void
  onPauseInitialScan?: (targetId: string) => void
  onEdit: (target: ScanTargetItem) => void
  onRemove: (targetId: string, label: string) => void
  scanLoading?: boolean
  activeScan?: ActiveScanSummary | null
  onCancelActiveScan?: (scanId: string) => void
  cancelLoadingForScanId?: string | null
  /** When using bulk selection */
  selectable?: boolean
  selected?: boolean
  onSelectToggle?: (targetId: string) => void
  /** Open fix prompt modal (My Targets) */
  onOpenFix?: (target: ScanTargetItem) => void
}

function formatClock(date: Date): string {
  return date.toLocaleString()
}

function formatMMSS(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds))
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}:${String(rem).padStart(2, '0')}`
}

export default function TargetCard({
  target,
  initialScanDelaySeconds = 300,
  onScanNow,
  onPauseInitialScan,
  onEdit,
  onRemove,
  scanLoading,
  activeScan: activeScanProp,
  onCancelActiveScan,
  cancelLoadingForScanId,
  selectable,
  selected,
  onSelectToggle,
  onOpenFix,
}: TargetCardProps) {
  const activeScan = activeScanProp ?? target.active_scan ?? null
  const label = target.display_name || target.source
  const typeLabel = TARGET_TYPE_LABELS[target.type] || target.type
  const icon = TYPE_ICONS[target.type] || '🎯'
  const autoScanOn = target.auto_scan?.enabled && (target.auto_scan?.interval_seconds || target.auto_scan?.event)
  const hasNoScanYet = !target.last_scan
  const [nowMs, setNowMs] = useState<number>(Date.now())

  useEffect(() => {
    const t = setInterval(() => setNowMs(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])

  const createdMs = target.created_at ? new Date(target.created_at).getTime() : NaN
  const dueMs = Number.isNaN(createdMs) ? NaN : createdMs + initialScanDelaySeconds * 1000
  const triggeredAt = target.initial_scan_triggered_at
    ? new Date(target.initial_scan_triggered_at)
    : null
  const hasTriggered = Boolean(triggeredAt && !Number.isNaN(triggeredAt.getTime()))
  const isDueKnown = !Number.isNaN(dueMs)
  const secondsUntilDue = isDueKnown ? Math.ceil((dueMs - nowMs) / 1000) : null
  const secondsPastDue = isDueKnown ? Math.max(0, Math.ceil((nowMs - dueMs) / 1000)) : null

  const firstScanStatusBadge = (() => {
    if (target.initial_scan_paused) return { text: 'Paused', color: 'rgba(173, 181, 189, 0.2)', border: 'rgba(173, 181, 189, 0.45)' }
    if (hasTriggered) return { text: 'Queued', color: 'rgba(25, 135, 84, 0.2)', border: 'rgba(25, 135, 84, 0.45)' }
    if (secondsUntilDue !== null && secondsUntilDue > 0) return { text: 'Auto-queue pending', color: 'rgba(13, 110, 253, 0.2)', border: 'rgba(13, 110, 253, 0.45)' }
    return { text: 'Due, waiting for scheduler', color: 'rgba(255, 193, 7, 0.2)', border: 'rgba(255, 193, 7, 0.45)' }
  })()

  return (
    <div
      style={{
        background: 'var(--glass-bg-main)',
        padding: '1.5rem',
        borderRadius: '8px',
        border: '1px solid var(--glass-border-main)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
            {selectable && onSelectToggle && (
              <input
                type="checkbox"
                checked={!!selected}
                onChange={() => onSelectToggle(target.id)}
                aria-label={`Select ${label}`}
                style={{ width: '1.1rem', height: '1.1rem', cursor: 'pointer', flexShrink: 0 }}
              />
            )}
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>
              {icon} {label.length > 60 ? label.slice(0, 60) + '…' : label}
            </h3>
            <span
              style={{
                padding: '0.2rem 0.5rem',
                borderRadius: '8px',
                fontSize: '0.7rem',
                background: 'var(--glass-border-main)',
                color: 'var(--text-secondary)',
              }}
            >
              {typeLabel}
            </span>
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', wordBreak: 'break-all' }}>
            {target.source}
          </div>
          {target.config?.branch != null && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Branch: {String(target.config.branch)}
            </div>
          )}
          {target.config?.tag != null && target.type === 'container_registry' && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Tag: {String(target.config.tag)}
            </div>
          )}
          {autoScanOn && (
            <div style={{ fontSize: '0.8rem', color: 'var(--color-info, #0dcaf0)', marginTop: '0.25rem' }}>
              Auto-scan: {target.auto_scan.mode === 'interval' && target.auto_scan.interval_seconds
                ? `every ${target.auto_scan.interval_seconds}s`
                : target.auto_scan.event || 'on'}
            </div>
          )}
          {target.next_scan_at && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              <strong>Next scan:</strong>{' '}
              {(() => {
                const next = new Date(target.next_scan_at!)
                const now = new Date()
                if (next.getTime() <= now.getTime()) return 'due'
                const min = Math.round((next.getTime() - now.getTime()) / 60000)
                if (min < 60) return `in ${min} min`
                const h = Math.floor(min / 60)
                if (h < 24) return `in ${h} h`
                return `at ${next.toLocaleString()}`
              })()}
            </div>
          )}
          {hasNoScanYet && (
            <div style={{ marginTop: '0.5rem', padding: '0.5rem', borderRadius: '6px', background: 'rgba(102, 126, 234, 0.12)', fontSize: '0.85rem', border: '1px solid rgba(102, 126, 234, 0.3)' }}>
              <div style={{ marginBottom: '0.35rem' }}>
                <span
                  style={{
                    display: 'inline-block',
                    padding: '0.12rem 0.45rem',
                    borderRadius: '999px',
                    fontSize: '0.72rem',
                    background: firstScanStatusBadge.color,
                    border: `1px solid ${firstScanStatusBadge.border}`,
                    color: 'var(--text-main)',
                  }}
                >
                  {firstScanStatusBadge.text}
                </span>
              </div>
              {target.initial_scan_paused ? (
                <span>First scan paused. Edit scanners above, then click <strong>Start first scan</strong> when ready.</span>
              ) : hasTriggered ? (
                <span>
                  <strong>First scan:</strong> queued at {formatClock(triggeredAt!)}
                  {onPauseInitialScan && (
                    <button
                      type="button"
                      onClick={() => onPauseInitialScan(target.id)}
                      style={{ marginLeft: '0.5rem', fontSize: '0.8rem', padding: '0.2rem 0.5rem' }}
                    >
                      Pause
                    </button>
                  )}
                </span>
              ) : isDueKnown && secondsUntilDue !== null && secondsUntilDue > 0 ? (
                <span>
                  <strong>First scan:</strong> in {formatMMSS(secondsUntilDue)} (at {formatClock(new Date(dueMs))})
                  {onPauseInitialScan && (
                    <button
                      type="button"
                      onClick={() => onPauseInitialScan(target.id)}
                      style={{ marginLeft: '0.5rem', fontSize: '0.8rem', padding: '0.2rem 0.5rem' }}
                    >
                      Pause
                    </button>
                  )}
                </span>
              ) : isDueKnown && secondsPastDue !== null ? (
                <span>
                  <strong>First scan:</strong> due since {formatMMSS(secondsPastDue)} (target enqueue time was {formatClock(new Date(dueMs))})
                  {onPauseInitialScan && (
                    <button
                      type="button"
                      onClick={() => onPauseInitialScan(target.id)}
                      style={{ marginLeft: '0.5rem', fontSize: '0.8rem', padding: '0.2rem 0.5rem' }}
                    >
                      Pause
                    </button>
                  )}
                </span>
              ) : null}
            </div>
          )}
          {target.scanners && target.scanners.length > 0 && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
              <strong>Scanners:</strong> {target.scanners.join(', ')}
            </div>
          )}
          {activeScan && ['pending', 'running'].includes(activeScan.status) && (
            <div
              style={{
                marginTop: '0.5rem',
                padding: '0.5rem',
                borderRadius: '6px',
                background: 'rgba(13, 110, 253, 0.12)',
                border: '1px solid rgba(13, 110, 253, 0.35)',
                fontSize: '0.85rem',
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <span
                style={{
                  padding: '0.12rem 0.45rem',
                  borderRadius: '999px',
                  fontSize: '0.72rem',
                  background:
                    activeScan.status === 'running' ? 'rgba(25, 135, 84, 0.25)' : 'rgba(255, 193, 7, 0.25)',
                  border: `1px solid ${activeScan.status === 'running' ? 'rgba(25, 135, 84, 0.5)' : 'rgba(255, 193, 7, 0.5)'}`,
                }}
              >
                Scan {activeScan.status === 'running' ? 'running' : 'queued'}
              </span>
              {activeScan.queue_position != null && (
                <span style={{ color: 'var(--text-secondary)' }}>Queue #{activeScan.queue_position}</span>
              )}
              <Link
                to="/scan"
                state={{ scan_id: activeScan.scan_id }}
                style={{ color: 'var(--accent, #0d6efd)', fontWeight: 500 }}
              >
                Open scan →
              </Link>
              <Link to="/my-scans" style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                My Scans
              </Link>
              {onCancelActiveScan && (
                <button
                  type="button"
                  onClick={() => onCancelActiveScan(activeScan.scan_id)}
                  disabled={cancelLoadingForScanId === activeScan.scan_id}
                  style={{ fontSize: '0.8rem', padding: '0.2rem 0.5rem', marginLeft: 'auto' }}
                >
                  {cancelLoadingForScanId === activeScan.scan_id ? 'Cancelling…' : 'Cancel scan'}
                </button>
              )}
            </div>
          )}
          {target.last_scan && (
            <div style={{ marginTop: '0.5rem', padding: '0.5rem', borderRadius: '6px', background: 'var(--glass-border-main)', fontSize: '0.85rem' }}>
              <div style={{ marginBottom: '0.25rem' }}>
                <strong>Last scan</strong>
                <span style={{ marginLeft: '0.5rem', color: 'var(--text-secondary)' }}>{target.last_scan.status}</span>
                {target.last_scan.completed_at && (
                  <span style={{ marginLeft: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    {new Date(target.last_scan.completed_at).toLocaleString()}
                  </span>
                )}
              </div>
              {target.last_scan.total_vulnerabilities > 0 ? (
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
                  {target.last_scan.critical_vulnerabilities > 0 && (
                    <span style={{ color: 'var(--color-critical, #dc3545)' }}>{target.last_scan.critical_vulnerabilities} critical</span>
                  )}
                  {target.last_scan.high_vulnerabilities > 0 && (
                    <span style={{ color: 'var(--color-warning, #fd7e14)' }}>{target.last_scan.high_vulnerabilities} high</span>
                  )}
                  {target.last_scan.medium_vulnerabilities > 0 && (
                    <span style={{ color: 'var(--color-info, #0dcaf0)' }}>{target.last_scan.medium_vulnerabilities} medium</span>
                  )}
                  {target.last_scan.low_vulnerabilities > 0 && (
                    <span style={{ color: 'var(--text-secondary)' }}>{target.last_scan.low_vulnerabilities} low</span>
                  )}
                </div>
              ) : (
                <div style={{ marginBottom: '0.25rem', color: 'var(--text-secondary)' }}>0 findings</div>
              )}
              {(target.last_scan.status === 'completed' || target.last_scan.status === 'failed') && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
                  <a
                    href={`/api/results/${target.last_scan.scan_id}/report`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: '0.85rem', color: 'var(--accent, #0d6efd)', textDecoration: 'none' }}
                  >
                    View report →
                  </a>
                  {onOpenFix && (
                    <button
                      type="button"
                      onClick={() => onOpenFix(target)}
                      style={{
                        fontSize: '0.85rem',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '6px',
                        border: '1px solid var(--glass-border-main)',
                        background: 'var(--glass-bg-main)',
                        cursor: 'pointer',
                        color: 'var(--text-main)',
                      }}
                    >
                      🔧 Fix
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        <button
          type="button"
          className="primary"
          onClick={() => onScanNow(target.id)}
          disabled={scanLoading}
        >
          {scanLoading ? 'Starting…' : hasNoScanYet && target.initial_scan_paused ? 'Start first scan' : 'Scan now'}
        </button>
        <button type="button" onClick={() => onEdit(target)}>
          Edit
        </button>
        <button
          type="button"
          onClick={() => onRemove(target.id, label)}
          style={{ color: 'var(--color-critical)' }}
        >
          Remove
        </button>
      </div>
    </div>
  )
}
