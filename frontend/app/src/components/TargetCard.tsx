import { Link } from 'react-router-dom'
import type { ScanTargetItem } from '../hooks/useTargets'

const TYPE_LABELS: Record<string, string> = {
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
  onScanNow: (targetId: string) => void
  onEdit: (target: ScanTargetItem) => void
  onRemove: (targetId: string, label: string) => void
  scanLoading?: boolean
}

export default function TargetCard({ target, onScanNow, onEdit, onRemove, scanLoading }: TargetCardProps) {
  const label = target.display_name || target.source
  const typeLabel = TYPE_LABELS[target.type] || target.type
  const icon = TYPE_ICONS[target.type] || '🎯'
  const autoScanOn = target.auto_scan?.enabled && (target.auto_scan?.interval_seconds || target.auto_scan?.event)

  return (
    <div
      style={{
        background: 'var(--glass-bg-dark)',
        padding: '1.5rem',
        borderRadius: '8px',
        border: '1px solid var(--glass-border-dark)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>
              {icon} {label.length > 60 ? label.slice(0, 60) + '…' : label}
            </h3>
            <span
              style={{
                padding: '0.2rem 0.5rem',
                borderRadius: '8px',
                fontSize: '0.7rem',
                background: 'var(--glass-border-dark)',
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
          {target.scanners && target.scanners.length > 0 && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
              <strong>Scanners:</strong> {target.scanners.join(', ')}
            </div>
          )}
          {target.last_scan && (
            <div style={{ marginTop: '0.5rem', padding: '0.5rem', borderRadius: '6px', background: 'var(--glass-border-dark)', fontSize: '0.85rem' }}>
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
                <Link
                  to="/scan"
                  state={{ scan_id: target.last_scan.scan_id, status: target.last_scan.status }}
                  style={{ fontSize: '0.85rem', color: 'var(--color-primary, #0d6efd)' }}
                >
                  View report →
                </Link>
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
          {scanLoading ? 'Starting…' : 'Scan now'}
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
