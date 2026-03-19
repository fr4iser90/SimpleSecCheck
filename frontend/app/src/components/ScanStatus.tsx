import type { ScanRunStatus } from '../types/scanStatus'

interface ScanStatusProps {
  status: {
    status: ScanRunStatus
    scan_id: string | null
    results_dir: string | null
    started_at: string | null
    error_code?: number | null
  }
}

const LABELS: Record<ScanRunStatus, string> = {
  idle: 'Idle',
  pending: 'Queued',
  running: 'Running…',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
  interrupted: 'Interrupted',
}

export default function ScanStatus({ status }: ScanStatusProps) {
  const getStatusBadge = () => {
    const className = `status-badge status-${status.status}`
    return <span className={className}>{LABELS[status.status] ?? status.status}</span>
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
        {getStatusBadge()}
        {status.scan_id && (
          <span style={{ opacity: 0.7 }}>Scan ID: {status.scan_id}</span>
        )}
      </div>
      {status.started_at && (
        <div style={{ opacity: 0.7, marginBottom: '0.5rem' }}>
          Started: {new Date(status.started_at).toLocaleString()}
        </div>
      )}
      {status.status === 'completed' && (
        <div style={{ marginTop: '1rem', color: '#28a745' }}>
          ✅ Scan completed successfully!
        </div>
      )}
    </div>
  )
}
