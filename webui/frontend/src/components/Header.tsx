import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'

interface ScanStatusData {
  status: 'idle' | 'running' | 'done' | 'error'
  scan_id: string | null
  results_dir: string | null
  started_at: string | null
  error_code?: number | null
  error_message?: string | null
}

interface ShutdownStatus {
  auto_shutdown_enabled: boolean
  shutdown_after_scan: boolean
  shutdown_delay: number
  idle_timeout: number
  shutdown_scheduled: boolean
  shutdown_in_seconds: number | null
  idle_timeout_remaining: number | null
  last_activity: number
}

export default function Header() {
  const navigate = useNavigate()
  const [scanStatus, setScanStatus] = useState<ScanStatusData>({
    status: 'idle',
    scan_id: null,
    results_dir: null,
    started_at: null,
  })
  const [shutdownStatus, setShutdownStatus] = useState<ShutdownStatus | null>(null)

  // Poll scan status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/scan/status')
        if (response.ok) {
          const status = await response.json()
          setScanStatus(status)
        }
      } catch (error) {
        console.error('Failed to fetch scan status:', error)
      }
    }

    // Fetch immediately
    fetchStatus()

    // Poll every 2 seconds if scan is running
    const interval = setInterval(() => {
      if (scanStatus.status === 'running') {
        fetchStatus()
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [scanStatus.status])

  // Poll shutdown status
  useEffect(() => {
    const fetchShutdownStatus = async () => {
      try {
        const response = await fetch('/api/shutdown/status')
        if (response.ok) {
          const status = await response.json()
          setShutdownStatus(status)
        }
      } catch (error) {
        console.error('Failed to fetch shutdown status:', error)
      }
    }

    // Fetch immediately
    fetchShutdownStatus()

    // Poll every 1 second if shutdown is scheduled
    const interval = setInterval(fetchShutdownStatus, 1000)

    return () => clearInterval(interval)
  }, [])

  const getStatusBadge = () => {
    if (scanStatus.status === 'idle') return null

    const badges = {
      running: { text: 'Running...', className: 'status-running' },
      done: { text: '✅ Done', className: 'status-done' },
      error: { text: '❌ Error', className: 'status-error' },
    }

    const badge = badges[scanStatus.status]
    if (!badge) return null

    return (
      <span className={`status-badge ${badge.className}`} style={{ marginRight: '0.5rem' }}>
        {badge.text}
      </span>
    )
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getTimerColor = (seconds: number | null): string => {
    if (seconds === null) return 'var(--text-dark)'
    if (seconds > 60) return '#ffc107' // Yellow
    if (seconds > 10) return '#fd7e14' // Orange
    return '#dc3545' // Red
  }

  const handleToggleAutoShutdown = async () => {
    if (!shutdownStatus) return
    
    try {
      const response = await fetch('/api/shutdown/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !shutdownStatus.auto_shutdown_enabled }),
      })
      if (response.ok) {
        const data = await response.json()
        setShutdownStatus({ ...shutdownStatus, auto_shutdown_enabled: data.auto_shutdown_enabled })
      }
    } catch (error) {
      console.error('Failed to toggle auto-shutdown:', error)
    }
  }

  const handleShutdownNow = async () => {
    if (!confirm('Are you sure you want to shutdown now?')) return
    
    try {
      await fetch('/api/shutdown/now', { method: 'POST' })
      // Shutdown will happen, no need to update state
    } catch (error) {
      console.error('Failed to shutdown:', error)
    }
  }

  return (
    <header className="header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h1 style={{ margin: 0 }}>🛡️ SimpleSecCheck</h1>
        </Link>
        {getStatusBadge()}
        {scanStatus.scan_id && (
          <span style={{ opacity: 0.7, fontSize: '0.9rem' }}>
            Scan ID: {scanStatus.scan_id}
          </span>
        )}
        {shutdownStatus && shutdownStatus.shutdown_in_seconds !== null && shutdownStatus.shutdown_in_seconds > 0 && (
          <span style={{ 
            color: getTimerColor(shutdownStatus.shutdown_in_seconds),
            fontWeight: 'bold',
            fontSize: '0.9rem',
          }}>
            ⏱️ {formatTime(shutdownStatus.shutdown_in_seconds)}
          </span>
        )}
        {shutdownStatus && (
          <label style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem', 
            fontSize: '0.9rem',
            cursor: 'pointer',
          }}>
            <input
              type="checkbox"
              checked={shutdownStatus.auto_shutdown_enabled}
              onChange={handleToggleAutoShutdown}
              style={{ cursor: 'pointer' }}
            />
            <span style={{ 
              textDecoration: shutdownStatus.auto_shutdown_enabled ? 'none' : 'line-through',
              opacity: shutdownStatus.auto_shutdown_enabled ? 1 : 0.6,
            }}>
              Auto-Shutdown
            </span>
          </label>
        )}
        {shutdownStatus?.auto_shutdown_enabled && (
          <button
            onClick={handleShutdownNow}
            style={{
              background: '#dc3545',
              border: 'none',
              borderRadius: '8px',
              color: 'white',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: 'bold',
            }}
            title="Shutdown now"
          >
            🛑
          </button>
        )}
      </div>
      <nav style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <Link to="/" style={{ color: 'inherit', textDecoration: 'none' }}>
          Home
        </Link>
        <Link to="/results" style={{ color: 'inherit', textDecoration: 'none' }}>
          Results
        </Link>
        <button
          onClick={() => navigate('/')}
          style={{
            background: 'var(--glass-bg-dark)',
            border: '1px solid var(--glass-border-dark)',
            borderRadius: '8px',
            color: 'var(--text-dark)',
            padding: '0.5rem 1rem',
            cursor: 'pointer',
            fontSize: '0.9rem',
          }}
        >
          New Scan
        </button>
      </nav>
    </header>
  )
}
