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
  selectable?: boolean
  selected?: boolean
  onSelectToggle?: (targetId: string) => void
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

  const firstScanStatus = (() => {
    if (target.initial_scan_paused) return { text: 'Paused', className: 'target-card__status-pill--paused' }
    if (hasTriggered) return { text: 'Queued', className: 'target-card__status-pill--queued' }
    if (secondsUntilDue !== null && secondsUntilDue > 0) {
      return { text: 'Auto-queue pending', className: 'target-card__status-pill--pending' }
    }
    return { text: 'Due, waiting for scheduler', className: 'target-card__status-pill--due' }
  })()

  return (
    <article className="target-card">
      <div className="target-card__head">
        <div className="target-card__title-row">
          {selectable && onSelectToggle && (
            <input
              type="checkbox"
              className="target-card__checkbox"
              checked={!!selected}
              onChange={() => onSelectToggle(target.id)}
              aria-label={`Select ${label}`}
            />
          )}
          <h3 className="target-card__title">
            <span aria-hidden>{icon} </span>
            {label.length > 60 ? `${label.slice(0, 60)}…` : label}
          </h3>
          <span className="target-card__type-badge">{typeLabel}</span>
        </div>
        <div className="target-card__source">{target.source}</div>
        {target.config?.branch != null && (
          <div className="target-card__meta">Branch: {String(target.config.branch)}</div>
        )}
        {target.config?.tag != null && target.type === 'container_registry' && (
          <div className="target-card__meta">Tag: {String(target.config.tag)}</div>
        )}
        {autoScanOn && (
          <div className="target-card__meta" style={{ color: 'var(--ds-info)' }}>
            Auto-scan:{' '}
            {target.auto_scan.mode === 'interval' && target.auto_scan.interval_seconds
              ? `every ${target.auto_scan.interval_seconds}s`
              : target.auto_scan.event || 'on'}
          </div>
        )}
        {target.next_scan_at && (
          <div className="target-card__meta">
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
          <div className="target-card__callout target-card__callout--info">
            <div style={{ marginBottom: '0.35rem' }}>
              <span className={`target-card__status-pill ${firstScanStatus.className}`}>
                {firstScanStatus.text}
              </span>
            </div>
            {target.initial_scan_paused ? (
              <span>
                First scan paused. Edit scanners, then click <strong>Start first scan</strong> when ready.
              </span>
            ) : hasTriggered ? (
              <span>
                <strong>First scan:</strong> queued at {formatClock(triggeredAt!)}
                {onPauseInitialScan && (
                  <button
                    type="button"
                    className="target-card__inline-btn"
                    onClick={() => onPauseInitialScan(target.id)}
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
                    className="target-card__inline-btn"
                    onClick={() => onPauseInitialScan(target.id)}
                  >
                    Pause
                  </button>
                )}
              </span>
            ) : isDueKnown && secondsPastDue !== null ? (
              <span>
                <strong>First scan:</strong> due since {formatMMSS(secondsPastDue)} (enqueue time{' '}
                {formatClock(new Date(dueMs))})
                {onPauseInitialScan && (
                  <button
                    type="button"
                    className="target-card__inline-btn"
                    onClick={() => onPauseInitialScan(target.id)}
                  >
                    Pause
                  </button>
                )}
              </span>
            ) : null}
          </div>
        )}
        {target.scanners && target.scanners.length > 0 && (
          <div className="target-card__meta">
            <strong>Scanners:</strong> {target.scanners.join(', ')}
          </div>
        )}
        {activeScan && ['pending', 'running'].includes(activeScan.status) && (
          <div className="target-card__callout target-card__callout--active">
            <div className="target-card__active-scan">
              <span
                className={`target-card__status-pill ${
                  activeScan.status === 'running'
                    ? 'target-card__status-pill--running'
                    : 'target-card__status-pill--scan-queued'
                }`}
              >
                Scan {activeScan.status === 'running' ? 'running' : 'queued'}
              </span>
              {activeScan.queue_position != null && (
                <span className="target-card__meta">Queue #{activeScan.queue_position}</span>
              )}
              <Link to="/scan" state={{ scan_id: activeScan.scan_id }} className="target-card__link">
                Open scan →
              </Link>
              <Link to="/my-scans" className="target-card__meta">
                My Scans
              </Link>
              {onCancelActiveScan && (
                <button
                  type="button"
                  className="target-card__inline-btn"
                  onClick={() => onCancelActiveScan(activeScan.scan_id)}
                  disabled={cancelLoadingForScanId === activeScan.scan_id}
                  style={{ marginLeft: 'auto' }}
                >
                  {cancelLoadingForScanId === activeScan.scan_id ? 'Cancelling…' : 'Cancel scan'}
                </button>
              )}
            </div>
          </div>
        )}
        {target.last_scan && (
          <div className="target-card__callout target-card__callout--last">
            <div style={{ marginBottom: '0.25rem' }}>
              <strong>Last scan</strong>
              <span className="target-card__meta" style={{ marginLeft: '0.5rem' }}>
                {target.last_scan.status}
              </span>
              {target.last_scan.completed_at && (
                <span className="target-card__meta" style={{ marginLeft: '0.5rem' }}>
                  {new Date(target.last_scan.completed_at).toLocaleString()}
                </span>
              )}
            </div>
            {target.last_scan.total_vulnerabilities > 0 ? (
              <div className="target-card__findings">
                {target.last_scan.critical_vulnerabilities > 0 && (
                  <span className="target-card__findings-critical">
                    {target.last_scan.critical_vulnerabilities} critical
                  </span>
                )}
                {target.last_scan.high_vulnerabilities > 0 && (
                  <span className="target-card__findings-high">
                    {target.last_scan.high_vulnerabilities} high
                  </span>
                )}
                {target.last_scan.medium_vulnerabilities > 0 && (
                  <span className="target-card__findings-medium">
                    {target.last_scan.medium_vulnerabilities} medium
                  </span>
                )}
                {target.last_scan.low_vulnerabilities > 0 && (
                  <span className="target-card__findings-low">
                    {target.last_scan.low_vulnerabilities} low
                  </span>
                )}
              </div>
            ) : (
              <div className="target-card__meta" style={{ marginBottom: '0.25rem' }}>
                0 findings
              </div>
            )}
            {(target.last_scan.status === 'completed' || target.last_scan.status === 'failed') && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
                <a
                  href={`/api/results/${target.last_scan.scan_id}/report`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="target-card__link"
                >
                  View report →
                </a>
                {onOpenFix && (
                  <button type="button" className="btn-secondary" onClick={() => onOpenFix(target)}>
                    Fix
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
      <div className="target-card__actions">
        <button
          type="button"
          className="primary"
          onClick={() => onScanNow(target.id)}
          disabled={scanLoading}
        >
          {scanLoading ? 'Starting…' : hasNoScanYet && target.initial_scan_paused ? 'Start first scan' : 'Scan now'}
        </button>
        <button type="button" className="btn-secondary" onClick={() => onEdit(target)}>
          Edit
        </button>
        <button type="button" className="btn-secondary target-card__btn-danger" onClick={() => onRemove(target.id, label)}>
          Remove
        </button>
      </div>
    </article>
  )
}
