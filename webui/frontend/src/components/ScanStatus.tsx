interface ScanStatusProps {
  status: {
    status: 'idle' | 'running' | 'done' | 'error'
    scan_id: string | null
    results_dir: string | null
    started_at: string | null
    error_code?: number | null
  }
}

export default function ScanStatus({ status }: ScanStatusProps) {
  const getStatusBadge = () => {
    const className = `status-badge status-${status.status}`
    const labels = {
      idle: 'Idle',
      running: 'Running...',
      done: 'Completed',
      error: 'Error',
    }
    return <span className={className}>{labels[status.status]}</span>
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
      {status.status === 'done' && (
        <div style={{ marginTop: '1rem', color: '#28a745' }}>
          ✅ Scan completed successfully!
        </div>
      )}
    </div>
  )
}
