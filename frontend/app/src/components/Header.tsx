import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useConfig } from '../hooks/useConfig'
import { useAuth } from '../hooks/useAuth'
import type { ScanRunStatus, ScanStatusState } from '../types/scanStatus'
import ThemeToggle from './ThemeToggle'

const GITHUB_REPO = 'https://github.com/fr4iser90/SimpleSecCheck'

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
          '/api/v1/scans/?status=running&limit=1&sort_by=created_at&sort_order=desc'
        )
        if (!running.ok || cancelled) return
        const runs = await running.json()
        let scanId: string | null = null
        if (Array.isArray(runs) && runs.length > 0) {
          scanId = runs[0].id
        }
        if (!scanId) {
          const pend = await apiFetch(
            '/api/v1/scans/?status=pending&limit=1&sort_by=created_at&sort_order=desc'
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
        <ThemeToggle />
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
          href={GITHUB_REPO}
          target="_blank"
          rel="noopener noreferrer"
          className="header-github-cta"
          title="SimpleSecCheck on GitHub"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
          </svg>
          GitHub
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
