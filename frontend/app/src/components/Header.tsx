import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useConfig } from '../hooks/useConfig'
import { useAuth } from '../hooks/useAuth'

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
  const { config } = useConfig()
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()
  const [scanStatus, setScanStatus] = useState<ScanStatusData>({
    status: 'idle',
    scan_id: null,
    results_dir: null,
    started_at: null,
  })
  const [shutdownStatus, setShutdownStatus] = useState<ShutdownStatus | null>(null)
  
  // Only show auto-shutdown if enabled in config
  const showAutoShutdown = config?.features.auto_shutdown ?? true

  // Poll scan status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const { apiFetch } = await import('../utils/apiClient')
        const response = await apiFetch('/api/scan/status')
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

  // Poll shutdown status (only if auto-shutdown is enabled)
  useEffect(() => {
    if (!showAutoShutdown) {
      setShutdownStatus(null)
      return
    }
    
    const fetchShutdownStatus = async () => {
      try {
        const { apiFetch } = await import('../utils/apiClient')
        const response = await apiFetch('/api/shutdown/status')
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
  }, [showAutoShutdown])

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
      const { apiFetch } = await import('../utils/apiClient')
      const response = await apiFetch('/api/shutdown/toggle', {
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
      const { apiFetch } = await import('../utils/apiClient')
      await apiFetch('/api/shutdown/now', { method: 'POST' })
      // Shutdown will happen, no need to update state
    } catch (error) {
      console.error('Failed to shutdown:', error)
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
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
        {showAutoShutdown && shutdownStatus && shutdownStatus.shutdown_in_seconds !== null && shutdownStatus.shutdown_in_seconds > 0 && (
          <span style={{ 
            color: getTimerColor(shutdownStatus.shutdown_in_seconds),
            fontWeight: 'bold',
            fontSize: '0.9rem',
          }}>
            ⏱️ {formatTime(shutdownStatus.shutdown_in_seconds)}
          </span>
        )}
        {showAutoShutdown && shutdownStatus && (
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
        {showAutoShutdown && shutdownStatus?.auto_shutdown_enabled && (
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
      <nav className="nav-links">
        <Link to="/" className="nav-pill nav-pill-primary">
          New Scan
        </Link>
        {config?.features.queue_enabled && (
          <>
            <Link to="/queue" className="nav-pill">
              Queue
            </Link>
            <Link to="/my-scans" className="nav-pill">
              My Scans
            </Link>
          </>
        )}
        {config?.is_production && (
          <Link to="/statistics" className="nav-pill">
            Statistics
          </Link>
        )}
        {isAuthenticated && user && (
          <Link to="/admin/settings" className="nav-pill">
            Admin Settings
          </Link>
        )}
        {isAuthenticated && user && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            background: '#f8f9fa',
            borderRadius: '8px',
            fontSize: '0.9rem',
          }}>
            <span style={{ color: '#666' }}>{user.email}</span>
            <button
              onClick={handleLogout}
              style={{
                background: 'transparent',
                border: '1px solid #ddd',
                borderRadius: '6px',
                color: '#666',
                padding: '0.25rem 0.75rem',
                cursor: 'pointer',
                fontSize: '0.85rem',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#f0f0f0'
                e.currentTarget.style.borderColor = '#999'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.borderColor = '#ddd'
              }}
            >
              Logout
            </button>
          </div>
        )}
        <a
          href="https://coff.ee/fr4iser"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            background: '#FFDD00',
            color: 'black',
            borderRadius: '8px',
            fontWeight: 500,
            textDecoration: 'none',
            fontSize: '0.9rem',
            transition: 'background-color 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = '#FFE44D'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = '#FFDD00'
          }}
        >
          <span>☕</span>
          Buy me a coffee
        </a>
        <a
          href="https://paypal.me/supportmysnacks"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            background: '#0070BA',
            color: 'white',
            borderRadius: '8px',
            fontWeight: 500,
            textDecoration: 'none',
            fontSize: '0.9rem',
            transition: 'background-color 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = '#0079C1'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = '#0070BA'
          }}
        >
          <span>💙</span>
          PayPal
        </a>
      </nav>
    </header>
  )
}
