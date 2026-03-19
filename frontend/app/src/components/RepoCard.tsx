import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { GitHubRepo, RepoScanStatus, getScoreColor, getVulnCount, getRepoStatus, getDaysSinceLastScan, getWarnings, getInitialScanCountdown } from '../utils/repoUtils'

interface RepoCardProps {
  repo: GitHubRepo
  scanStatus?: RepoScanStatus
  onScanNow: (repoId: string) => void
  onEdit: (repo: GitHubRepo) => void
  onRemove: (repoId: string, repoName: string) => void
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  const now = Date.now()
  const min = Math.floor((now - then) / 60000)
  if (min < 1) return 'just now'
  if (min < 60) return `${min} min ago`
  const h = Math.floor(min / 60)
  if (h < 24) return `${h} h ago`
  const d = Math.floor(h / 24)
  return `${d} day${d !== 1 ? 's' : ''} ago`
}

export default function RepoCard({ repo, scanStatus, onScanNow, onEdit, onRemove }: RepoCardProps) {
  const status = getRepoStatus(repo, scanStatus)
  const warnings = getWarnings(repo, scanStatus)
  const score = repo.score ?? 0
  const vulns = repo.vulnerabilities || { critical: 0, high: 0, medium: 0, low: 0 }
  const totalVulns = getVulnCount(repo)
  const daysSince = getDaysSinceLastScan(repo)
  const [countdown, setCountdown] = useState<number | null>(getInitialScanCountdown(repo))
  
  // Update countdown every second
  useEffect(() => {
    if (countdown === null || countdown <= 0) {
      return
    }
    
    const interval = setInterval(() => {
      const newCountdown = getInitialScanCountdown(repo)
      setCountdown(newCountdown)
    }, 1000)
    
    return () => clearInterval(interval)
  }, [repo, countdown])
  
  return (
    <div
      style={{
        background: 'var(--glass-bg-dark)',
        padding: '1.5rem',
        borderRadius: '8px',
        border: `1px solid ${status.color}40`,
        boxShadow: warnings.length > 0 ? `0 0 0 1px ${status.color}60` : undefined
      }}
    >
      {/* Header with Repo Name and Status Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <h3 style={{ margin: 0 }}>
              📦 {repo.repo_owner ? `${repo.repo_owner}/` : ''}{repo.repo_name}
            </h3>
            <span style={{
              padding: '0.25rem 0.75rem',
              borderRadius: '12px',
              fontSize: '0.75rem',
              fontWeight: 'bold',
              background: `${status.color}20`,
              color: status.color,
              border: `1px solid ${status.color}40`
            }}>
              {status.label}
            </span>
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
            🔗 {repo.repo_url}
          </div>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            <span>🌿 Branch: <strong>{repo.branch}</strong></span>
            <span>🔄 Auto-scan: <strong>{repo.auto_scan_enabled ? 'ON' : 'OFF'}</strong></span>
            {repo.auto_scan_enabled && (
              <span>📤 Scan on push: <strong>{repo.scan_on_push ? 'ON' : 'OFF'}</strong></span>
            )}
            {repo.scan_on_push && repo.last_webhook_triggered_at && (
              <span>🔗 Last webhook: <strong>{formatRelativeTime(repo.last_webhook_triggered_at)}</strong></span>
            )}
            {repo.last_scan && (
              <span>📊 Last scan: <strong>{daysSince !== null ? `${daysSince} day${daysSince !== 1 ? 's' : ''} ago` : new Date(repo.last_scan.created_at).toLocaleString()}</strong></span>
            )}
          </div>
        </div>
      </div>

      {/* Initial Scan Countdown */}
      {countdown !== null && countdown > 0 && (
        <div style={{
          marginBottom: '1rem',
          padding: '0.75rem',
          background: 'rgba(102, 126, 234, 0.1)',
          border: '1px solid rgba(102, 126, 234, 0.3)',
          borderRadius: '6px',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <span>⏱️</span>
          <span>
            Initial scan will start in <strong>{countdown} second{countdown !== 1 ? 's' : ''}</strong>
          </span>
        </div>
      )}

      {/* Queue Status */}
      {scanStatus?.has_active_scan && scanStatus.status === 'pending' && scanStatus.queue_position !== null && (
        <div style={{
          marginBottom: '1rem',
          padding: '1rem',
          background: 'rgba(255, 193, 7, 0.15)',
          border: '1px solid rgba(255, 193, 7, 0.4)',
          borderRadius: '8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', fontWeight: 'bold' }}>
            <span>⏳</span>
            <span>Scan is queued</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
            <span style={{ opacity: 0.9 }}>Position in queue:</span>
            <strong style={{ fontSize: '1.25rem', color: 'var(--color-medium)' }}>
              #{scanStatus.queue_position}
            </strong>
          </div>
          {scanStatus.queue_position > 1 && (
            <div style={{ fontSize: '0.8rem', opacity: 0.8, fontStyle: 'italic' }}>
              Estimated wait: ~{Math.ceil(scanStatus.queue_position * 2)} minutes
            </div>
          )}
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div style={{
          marginBottom: '1rem',
          padding: '0.75rem',
          background: 'rgba(255, 193, 7, 0.1)',
          border: '1px solid rgba(255, 193, 7, 0.3)',
          borderRadius: '6px',
          fontSize: '0.85rem'
        }}>
          {warnings.map((warning, idx) => (
            <div key={idx} style={{ marginBottom: idx < warnings.length - 1 ? '0.5rem' : 0 }}>
              {warning}
            </div>
          ))}
        </div>
      )}

      {/* Score and Vulnerabilities Section */}
      <div style={{
        marginBottom: '1rem',
        padding: '1rem',
        background: 'rgba(0, 0, 0, 0.2)',
        borderRadius: '8px'
      }}>
        {score > 0 ? (
          <>
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>Security Score:</span>
                <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: getScoreColor(score) }}>
                  {score}/100
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '12px',
                background: 'rgba(0, 0, 0, 0.3)',
                borderRadius: '6px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${score}%`,
                  height: '100%',
                  background: getScoreColor(score),
                  transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
            <div style={{
              display: 'flex',
              gap: '1rem',
              flexWrap: 'wrap',
              fontSize: '0.85rem',
              paddingTop: '0.75rem',
              borderTop: '1px solid rgba(255, 255, 255, 0.1)'
            }}>
              <span style={{ color: 'var(--color-critical)' }}>
                ⚠️ Critical: <strong>{vulns.critical || 0}</strong>
              </span>
              <span style={{ color: 'var(--color-high)' }}>
                🔴 High: <strong>{vulns.high || 0}</strong>
              </span>
              <span style={{ color: 'var(--color-medium)' }}>
                🟠 Medium: <strong>{vulns.medium || 0}</strong>
              </span>
              <span style={{ color: 'var(--color-low)' }}>
                🟡 Low: <strong>{vulns.low || 0}</strong>
              </span>
              <span style={{ marginLeft: 'auto', fontWeight: 'bold' }}>
                Total: <strong>{totalVulns}</strong>
              </span>
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            No scan data available yet. Run a scan to see security score and vulnerabilities.
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {repo.last_scan?.scan_id && (
          <Link
            to={`/scan?scan_id=${repo.last_scan.scan_id}`}
            style={{
              padding: '0.5rem 1rem',
              background: 'var(--glass-bg-dark)',
              border: '1px solid var(--glass-border-dark)',
              borderRadius: '6px',
              textDecoration: 'none',
              color: 'var(--text-dark)',
              fontSize: '0.9rem'
            }}
          >
            View Results
          </Link>
        )}
        <button
          onClick={() => onScanNow(repo.id)}
          style={{ fontSize: '0.9rem', padding: '0.5rem 1rem' }}
          disabled={scanStatus?.has_active_scan}
        >
          {scanStatus?.has_active_scan ? '⏳ Scan Queued' : 'Scan Now'}
        </button>
        <button
          onClick={() => onEdit(repo)}
          style={{ fontSize: '0.9rem', padding: '0.5rem 1rem' }}
        >
          ⚙️ Settings
        </button>
        <button
          onClick={() => onRemove(repo.id, repo.repo_name)}
          style={{ fontSize: '0.9rem', padding: '0.5rem 1rem', background: 'var(--color-critical)' }}
        >
          🗑️ Remove
        </button>
      </div>
    </div>
  )
}
