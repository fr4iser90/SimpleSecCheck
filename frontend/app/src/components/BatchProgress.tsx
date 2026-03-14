import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface RepositoryScan {
  repository_url: string
  repository_name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  scan_id: string | null
  started_at: string | null
  finished_at: string | null
  error_message: string | null
  results_dir: string | null
  findings_count: number | null
}

interface BatchScanProgress {
  batch_id: string
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'stopped'
  total_repos: number
  completed_repos: number
  failed_repos: number
  skipped_repos: number
  current_repo: string | null
  started_at: string | null
  finished_at: string | null
  repositories: RepositoryScan[]
}

interface BatchProgressProps {
  batchId: string
}

export default function BatchProgress({ batchId }: BatchProgressProps) {
  const [progress, setProgress] = useState<BatchScanProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const response = await fetch(`/api/bulk/status?batch_id=${batchId}`)
        if (!response.ok) {
          throw new Error('Failed to fetch batch progress')
        }
        const data = await response.json()
        setProgress(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchProgress()
    
    // Poll every 2 seconds if still running
    const interval = setInterval(() => {
      if (progress?.status === 'running' || progress?.status === 'paused') {
        fetchProgress()
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [batchId, progress?.status])

  const handlePause = async () => {
    try {
      const response = await fetch('/api/bulk/pause', { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        setProgress(data)
      }
    } catch (err) {
      console.error('Failed to pause:', err)
    }
  }

  const handleResume = async () => {
    try {
      const response = await fetch('/api/bulk/resume', { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        setProgress(data)
      }
    } catch (err) {
      console.error('Failed to resume:', err)
    }
  }

  const handleStop = async () => {
    if (!confirm('Are you sure you want to stop the batch scan?')) return
    
    try {
      const response = await fetch('/api/bulk/stop', { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        setProgress(data)
      }
    } catch (err) {
      console.error('Failed to stop:', err)
    }
  }

  const getStatusIcon = (status: RepositoryScan['status']) => {
    switch (status) {
      case 'completed': return '✓'
      case 'running': return '⏳'
      case 'failed': return '❌'
      case 'skipped': return '⏸'
      default: return '⏸'
    }
  }

  const getStatusColor = (status: RepositoryScan['status']) => {
    switch (status) {
      case 'completed': return '#28a745'
      case 'running': return '#007bff'
      case 'failed': return '#dc3545'
      case 'skipped': return '#6c757d'
      default: return '#6c757d'
    }
  }

  if (loading) {
    return <div>Loading batch progress...</div>
  }

  if (error || !progress) {
    return <div style={{ color: '#dc3545' }}>Error: {error || 'Failed to load progress'}</div>
  }

  const percentage = progress.total_repos > 0 
    ? ((progress.completed_repos + progress.failed_repos + progress.skipped_repos) / progress.total_repos) * 100 
    : 0

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h2>Batch Scan Progress</h2>
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span>Batch ID: <strong>{progress.batch_id}</strong></span>
            <span style={{
              padding: '0.25rem 0.75rem',
              borderRadius: '4px',
              background: progress.status === 'running' ? '#007bff' : progress.status === 'completed' ? '#28a745' : '#6c757d',
              color: '#fff',
              fontSize: '0.875rem',
              fontWeight: 'bold'
            }}>
              {progress.status.toUpperCase()}
            </span>
          </div>
          
          <div style={{
            width: '100%',
            height: '24px',
            background: '#e9ecef',
            borderRadius: '12px',
            overflow: 'hidden',
            marginBottom: '0.5rem'
          }}>
            <div style={{
              width: `${percentage}%`,
              height: '100%',
              background: '#28a745',
              transition: 'width 0.3s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '0.75rem',
              fontWeight: 'bold'
            }}>
              {percentage.toFixed(0)}%
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#6c757d' }}>
            <span>✓ {progress.completed_repos} completed</span>
            <span>❌ {progress.failed_repos} failed</span>
            <span>⏸ {progress.skipped_repos} skipped</span>
            <span>⏳ {progress.total_repos - progress.completed_repos - progress.failed_repos - progress.skipped_repos} pending</span>
          </div>

          {progress.current_repo && (
            <div style={{
              marginTop: '0.5rem',
              padding: '0.5rem',
              background: 'rgba(0, 123, 255, 0.1)',
              borderRadius: '4px',
              fontSize: '0.875rem'
            }}>
              Currently scanning: <strong>{progress.current_repo}</strong>
            </div>
          )}
        </div>

        {/* Control Buttons */}
        {progress.status === 'running' && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={handlePause}
              style={{
                padding: '0.5rem 1rem',
                border: '1px solid #ffc107',
                borderRadius: '4px',
                background: '#fff',
                color: '#856404',
                cursor: 'pointer'
              }}
            >
              ⏸ Pause
            </button>
            <button
              onClick={handleStop}
              style={{
                padding: '0.5rem 1rem',
                border: '1px solid #dc3545',
                borderRadius: '4px',
                background: '#fff',
                color: '#dc3545',
                cursor: 'pointer'
              }}
            >
              ⏹ Stop
            </button>
          </div>
        )}

        {progress.status === 'paused' && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={handleResume}
              style={{
                padding: '0.5rem 1rem',
                border: '1px solid #28a745',
                borderRadius: '4px',
                background: '#28a745',
                color: '#fff',
                cursor: 'pointer'
              }}
            >
              ▶ Resume
            </button>
            <button
              onClick={handleStop}
              style={{
                padding: '0.5rem 1rem',
                border: '1px solid #dc3545',
                borderRadius: '4px',
                background: '#fff',
                color: '#dc3545',
                cursor: 'pointer'
              }}
            >
              ⏹ Stop
            </button>
          </div>
        )}
      </div>

      {/* Repository List */}
      <div style={{
        maxHeight: '500px',
        overflowY: 'auto',
        border: '1px solid #ced4da',
        borderRadius: '6px',
        padding: '0.5rem'
      }}>
        {progress.repositories.map((repo, index) => (
          <div
            key={index}
            style={{
              padding: '0.75rem',
              borderBottom: index < progress.repositories.length - 1 ? '1px solid #e9ecef' : 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '1rem'
            }}
          >
            <span style={{
              fontSize: '1.25rem',
              color: getStatusColor(repo.status)
            }}>
              {getStatusIcon(repo.status)}
            </span>
            
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>
                {repo.repository_name}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem' }}>
                {repo.repository_url}
              </div>
              {repo.findings_count !== null && (
                <div style={{ fontSize: '0.75rem', color: '#6c757d' }}>
                  Findings: {repo.findings_count}
                </div>
              )}
              {repo.error_message && (
                <div style={{ fontSize: '0.75rem', color: '#dc3545', marginTop: '0.25rem' }}>
                  Error: {repo.error_message}
                </div>
              )}
            </div>

            {repo.status === 'completed' && repo.results_dir && (
              <button
                onClick={() => navigate('/my-scans')}
                style={{
                  padding: '0.25rem 0.75rem',
                  fontSize: '0.75rem',
                  border: '1px solid #28a745',
                  borderRadius: '4px',
                  background: '#28a745',
                  color: '#fff',
                  cursor: 'pointer'
                }}
              >
                View Report
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
