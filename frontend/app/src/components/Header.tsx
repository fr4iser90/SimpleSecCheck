import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useConfig } from '../hooks/useConfig'
import { useAuth } from '../hooks/useAuth'
import type { ScanRunStatus, ScanStatusState } from '../types/scanStatus'

export default function Header() {
  const { config } = useConfig()
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()
  const [scanStatus, setScanStatus] = useState<ScanStatusState>({
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

  useEffect(() => {
    let cancelled = false
    const tick = async () => {
      try {
        const { apiFetch } = await import('../utils/apiClient')
        const running = await apiFetch(
          '/api/v1/scans?status=running&limit=1&sort_by=created_at&sort_order=desc'
        )
        if (!running.ok || cancelled) return
        const runs = await running.json()
        let scanId: string | null = null
        if (Array.isArray(runs) && runs.length > 0) {
          scanId = runs[0].id
        }
        if (!scanId) {
          const pend = await apiFetch(
            '/api/v1/scans?status=pending&limit=1&sort_by=created_at&sort_order=desc'
          )
          if (!pend.ok || cancelled) return
          const ps = await pend.json()
          if (Array.isArray(ps) && ps.length > 0) {
            setScanStatus({
              status: 'pending',
              scan_id: ps[0].id,
              results_dir: null,
              started_at: ps[0].started_at || null,
            })
            return
          }
        }
        if (!scanId) {
          setScanStatus({
            status: 'idle',
            scan_id: null,
            results_dir: null,
            started_at: null,
          })
          return
        }
        const sr = await apiFetch(`/api/v1/scans/${encodeURIComponent(scanId)}/status`)
        if (!sr.ok || cancelled) return
        const d = await sr.json()
        setScanStatus({
          status: d.status as ScanRunStatus,
          scan_id: d.scan_id,
          results_dir: d.scan_id,
          started_at: d.started_at ?? null,
        })
      } catch (e) {
        console.error('Header scan status poll:', e)
      }
    }
    void tick()
    const iv = setInterval(tick, 4000)
    return () => {
      cancelled = true
      clearInterval(iv)
    }
  }, [])

  const getStatusBadge = () => {
    if (scanStatus.status === 'idle') return null

    const badges: Partial<
      Record<
        ScanRunStatus,
        { text: string; className: string }
      >
    > = {
      running: { text: 'Running…', className: 'status-running' },
      pending: { text: '⏳ Queued', className: 'status-running' },
      completed: { text: '✅ Done', className: 'status-done' },
      failed: { text: '❌ Failed', className: 'status-error' },
      cancelled: { text: 'Cancelled', className: 'status-error' },
      interrupted: { text: '⚠️ Interrupted', className: 'status-error' },
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
          <Link to="/my-targets" className="nav-pill">
            My Targets
          </Link>
        )}
        <Link to="/statistics" className="nav-pill">
          Statistics
        </Link>
        <Link to="/capabilities" className="nav-pill" title="What guests vs signed-in users can do">
          Guest vs account
        </Link>
        {isAuthenticated && user && isAdmin && (
          <div className="dropdown" ref={adminMenuRef}>
            <button
              type="button"
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
              type="button"
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
              <Link to="/my-targets" className="dropdown-item" onClick={() => setShowUserMenu(false)}>
                My Targets
              </Link>
              <Link to="/api-keys" className="dropdown-item" onClick={() => setShowUserMenu(false)}>
                API Keys
              </Link>
              <div className="dropdown-divider"></div>
              <button
                type="button"
                className="dropdown-item"
                onClick={() => {
                  setShowUserMenu(false)
                  void handleLogout()
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
