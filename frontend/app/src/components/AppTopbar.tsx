import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useHeaderScanStatus } from '../hooks/useHeaderScanStatus'
import type { ScanRunStatus } from '../types/scanStatus'
import AppIcon from './AppIcon'
import ThemeToggle from './ThemeToggle'

const ROUTE_LABELS: Record<string, string> = {
  '/': 'New Scan',
  '/scan': 'Queue',
  '/bulk': 'Bulk Scan',
  '/queue': 'Queue',
  '/my-scans': 'My Scans',
  '/my-targets': 'My Targets',
  '/statistics': 'Statistics',
  '/capabilities': 'Guest vs account',
  '/profile': 'Profile',
  '/api-keys': 'API Keys',
  '/admin': 'Admin',
  '/admin/settings': 'System Settings',
  '/admin/users': 'User Management',
  '/admin/feature-flags': 'Feature Flags',
  '/admin/auth': 'Auth Settings',
  '/admin/legal': 'Legal Settings',
  '/admin/execution': 'Execution',
  '/admin/queue': 'Queue Settings',
  '/admin/policies': 'Security Policies',
  '/admin/health': 'System Health',
  '/admin/sse-debug': 'SSE Debug',
  '/admin/audit-log': 'Audit Log',
  '/admin/security/ip-control': 'IP Control',
  '/admin/scanner': 'Scan Engine',
  '/admin/tool-duration': 'Tool Duration',
  '/admin/tool-settings': 'Tool Settings',
}

function getBreadcrumb(pathname: string): { parent?: { label: string; to: string }; current: string } {
  if (ROUTE_LABELS[pathname]) {
    if (pathname === '/' || pathname === '/admin') {
      return { current: ROUTE_LABELS[pathname] }
    }
    if (pathname.startsWith('/admin/')) {
      return { parent: { label: 'Admin', to: '/admin' }, current: ROUTE_LABELS[pathname] || 'Admin' }
    }
    return { parent: { label: 'Scans', to: '/' }, current: ROUTE_LABELS[pathname] }
  }
  return { current: 'SimpleSecCheck' }
}

function scanPillMeta(status: ScanRunStatus): { text: string; className: string; to?: string } | null {
  switch (status) {
    case 'running':
      return { text: 'Scan running', className: '', to: '/scan' }
    case 'pending':
      return { text: 'Scan queued', className: '', to: '/queue' }
    case 'completed':
      return { text: 'Scan completed', className: ' app-shell__scan-pill--done', to: '/scan' }
    case 'failed':
    case 'cancelled':
    case 'interrupted':
      return { text: 'Scan failed', className: ' app-shell__scan-pill--error', to: '/scan' }
    default:
      return null
  }
}

export default function AppTopbar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { isAuthenticated, user, logout } = useAuth()
  const scanStatus = useHeaderScanStatus()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  const crumb = getBreadcrumb(pathname)
  const pill = scanPillMeta(scanStatus.status)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <header className="app-shell__topbar">
      <nav className="app-shell__breadcrumb" aria-label="Breadcrumb">
        {crumb.parent ? (
          <>
            <Link to={crumb.parent.to}>{crumb.parent.label}</Link>
            <span className="app-shell__breadcrumb-sep">/</span>
          </>
        ) : null}
        <span className="app-shell__breadcrumb-current">{crumb.current}</span>
      </nav>

      <div className="app-shell__topbar-actions">
        {pill ? (
          <Link to={pill.to || '/scan'} className={`app-shell__scan-pill${pill.className}`}>
            <span className="app-shell__scan-pill-dot" />
            {pill.text}
          </Link>
        ) : null}

        <ThemeToggle />

        {isAuthenticated && user ? (
          <div className="app-shell__dropdown" ref={userMenuRef}>
            <button
              type="button"
              className="app-shell__dropdown-toggle"
              onClick={() => setShowUserMenu(!showUserMenu)}
              aria-expanded={showUserMenu}
            >
              <span>{user.email}</span>
              <AppIcon name="chevron-down" size={14} />
            </button>
            <div className={`app-shell__dropdown-menu${showUserMenu ? ' app-shell__dropdown-menu--open' : ''}`}>
              <Link to="/profile" className="app-shell__dropdown-item" onClick={() => setShowUserMenu(false)}>
                Profile
              </Link>
              <Link to="/my-targets" className="app-shell__dropdown-item" onClick={() => setShowUserMenu(false)}>
                My Targets
              </Link>
              <Link to="/api-keys" className="app-shell__dropdown-item" onClick={() => setShowUserMenu(false)}>
                API Keys
              </Link>
              <div className="app-shell__dropdown-divider" />
              <button
                type="button"
                className="app-shell__dropdown-item"
                onClick={() => {
                  setShowUserMenu(false)
                  void handleLogout()
                }}
              >
                Logout
              </button>
            </div>
          </div>
        ) : (
          <Link to="/login" className="app-shell__sign-in">
            Sign in
          </Link>
        )}

        <a
          href="https://github.com/fr4iser90/SimpleSecCheck"
          target="_blank"
          rel="noopener noreferrer"
          className="theme-toggle-button"
          title="GitHub"
          aria-label="GitHub repository"
        >
          <AppIcon name="github" size={16} />
        </a>
      </div>
    </header>
  )
}
