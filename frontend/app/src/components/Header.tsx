import { useState, useEffect, useRef } from 'react'
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
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showAdminMenu, setShowAdminMenu] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const adminMenuRef = useRef<HTMLDivElement>(null)
  
  const isAdmin = user?.role === 'admin'

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

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false)
      }
      if (adminMenuRef.current && !adminMenuRef.current.contains(event.target as Node)) {
        setShowAdminMenu(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

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
      </div>
      <nav className="nav-links">
        <Link to="/" className="nav-pill nav-pill-primary">
          New Scan
        </Link>
        <Link to="/queue" className="nav-pill">
          Queue
        </Link>
        {isAuthenticated && (
          <Link to="/my-scans" className="nav-pill">
            My Scans
          </Link>
        )}
        {isAuthenticated && (
          <Link to="/my-repos" className="nav-pill">
            My Repos
          </Link>
        )}
        <Link to="/statistics" className="nav-pill">
          Statistics
        </Link>
        {isAuthenticated && user && isAdmin && (
          <div className="dropdown" ref={adminMenuRef}>
            <button
              className="dropdown-toggle"
              onClick={() => {
                setShowAdminMenu(!showAdminMenu)
                setShowUserMenu(false)
              }}
            >
              <span>⚙️ Admin</span>
              <span>▼</span>
            </button>
            <div className={`dropdown-menu ${showAdminMenu ? 'show' : ''}`}>
              <Link to="/admin" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Dashboard
              </Link>
              <Link to="/admin/settings" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                System Settings
              </Link>
              <Link to="/admin/auth" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Auth Settings
              </Link>
              <Link to="/admin/users" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                User Management
              </Link>
              <Link to="/admin/feature-flags" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Feature Flags
              </Link>
              <Link to="/admin/security" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Security Policies
              </Link>
              <Link to="/admin/audit-log" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Audit Log
              </Link>
              <Link to="/admin/security/ip-control" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                IP & Abuse Protection
              </Link>
              <Link to="/admin/scanner" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Scan Engine Management
              </Link>
              <Link to="/admin/tool-duration" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Tool duration (exact per scanner)
              </Link>
              <Link to="/admin/tool-settings" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Tool settings (DB overrides)
              </Link>
              <Link to="/admin/vulnerabilities" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Vulnerability Database
              </Link>
              <Link to="/admin/scan-policies" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Scan Policies
              </Link>
              <Link to="/admin/notifications" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                Notification Management
              </Link>
              <Link to="/admin/health" className="dropdown-item" onClick={() => setShowAdminMenu(false)}>
                System Health
              </Link>
            </div>
          </div>
        )}
        {isAuthenticated && user && (
          <div className="dropdown" ref={userMenuRef}>
            <button
              className="dropdown-toggle"
              onClick={() => {
                setShowUserMenu(!showUserMenu)
                setShowAdminMenu(false)
              }}
            >
              <span>{user.email}</span>
              <span>▼</span>
            </button>
            <div className={`dropdown-menu ${showUserMenu ? 'show' : ''}`}>
              <Link to="/profile" className="dropdown-item" onClick={() => setShowUserMenu(false)}>
                Profile
              </Link>
              <Link to="/my-repos" className="dropdown-item" onClick={() => setShowUserMenu(false)}>
                My GitHub Repos
              </Link>
              <Link to="/api-keys" className="dropdown-item" onClick={() => setShowUserMenu(false)}>
                API Keys
              </Link>
              <div className="dropdown-divider"></div>
              <button
                className="dropdown-item"
                onClick={() => {
                  setShowUserMenu(false)
                  handleLogout()
                }}
              >
                Logout
              </button>
            </div>
          </div>
        )}
        {!isAuthenticated && config?.auth_mode !== 'free' && (
          <Link to="/login" className="nav-pill">
            Login
          </Link>
        )}
        {!isAuthenticated && config?.auth_mode === 'free' && (
          <Link to="/login" className="nav-pill" style={{ opacity: 0.7 }}>
            Login (Optional)
          </Link>
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
