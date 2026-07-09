import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useConfig } from '../hooks/useConfig'
import LegalFooterLinks, { useLegalConfig } from './Legal'
import AppIcon from './AppIcon'

const GITHUB_REPO = 'https://github.com/fr4iser90/SimpleSecCheck'
const LICENSE = `${GITHUB_REPO}/blob/main/LICENSE`

interface NavItem {
  to: string
  label: string
  icon: string
  auth?: boolean
  admin?: boolean
}

const SCAN_NAV: NavItem[] = [
  { to: '/', label: 'New Scan', icon: 'scan' },
  { to: '/queue', label: 'Queue', icon: 'queue' },
  { to: '/my-scans', label: 'My Scans', icon: 'history', auth: true },
  { to: '/my-targets', label: 'My Targets', icon: 'target', auth: true },
]

const INSIGHTS_NAV: NavItem[] = [
  { to: '/statistics', label: 'Statistics', icon: 'chart' },
  { to: '/capabilities', label: 'Guest vs account', icon: 'info' },
  { to: '/admin', label: 'Admin', icon: 'settings', admin: true },
]

function NavSection({
  label,
  items,
  pathname,
  isAuthenticated,
  isAdmin,
}: {
  label: string
  items: NavItem[]
  pathname: string
  isAuthenticated: boolean
  isAdmin: boolean
}) {
  const visible = items.filter((item) => {
    if (item.auth && !isAuthenticated) return false
    if (item.admin && !isAdmin) return false
    return true
  })
  if (visible.length === 0) return null

  return (
    <div className="app-shell__nav-section">
      <span className="app-shell__nav-label">{label}</span>
      {visible.map((item) => {
        const active =
          item.to === '/'
            ? pathname === '/'
            : pathname === item.to || pathname.startsWith(`${item.to}/`)
        return (
          <Link
            key={item.to}
            to={item.to}
            className={`app-shell__nav-link${active ? ' app-shell__nav-link--active' : ''}`}
          >
            <AppIcon name={item.icon} />
            {item.label}
          </Link>
        )
      })}
    </div>
  )
}

function userInitials(email: string): string {
  const local = email.split('@')[0] || 'U'
  const parts = local.split(/[._-]/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return local.slice(0, 2).toUpperCase()
}

export default function AppSidebar() {
  const { pathname } = useLocation()
  const { isAuthenticated, user } = useAuth()
  const { config } = useConfig()
  const legal = useLegalConfig()
  const isAdmin = user?.role === 'admin'

  return (
    <aside className="app-shell__sidebar">
      <Link to="/" className="app-shell__brand">
        <span className="app-shell__brand-icon">
          <AppIcon name="shield" size={15} />
        </span>
        <span className="app-shell__brand-text">
          <span className="app-shell__brand-name">SimpleSecCheck</span>
          <span className="app-shell__brand-plan">Security Platform</span>
        </span>
      </Link>

      <nav className="app-shell__nav" aria-label="Main navigation">
        <NavSection
          label="Scan"
          items={SCAN_NAV}
          pathname={pathname}
          isAuthenticated={isAuthenticated}
          isAdmin={!!isAdmin}
        />
        <NavSection
          label="Insights"
          items={INSIGHTS_NAV}
          pathname={pathname}
          isAuthenticated={isAuthenticated}
          isAdmin={!!isAdmin}
        />
      </nav>

      {isAuthenticated && user ? (
        <div className="app-shell__sidebar-user">
          <span className="app-shell__avatar">{userInitials(user.email)}</span>
          <div className="app-shell__user-meta">
            <div className="app-shell__user-name">{user.email.split('@')[0]}</div>
            <div className="app-shell__user-email">{user.email}</div>
          </div>
        </div>
      ) : (
        <div className="app-shell__sidebar-user">
          <span className="app-shell__avatar">G</span>
          <div className="app-shell__user-meta">
            <div className="app-shell__user-name">Guest</div>
            <div className="app-shell__user-email">
              {config?.auth_mode === 'free' ? 'Login optional' : 'Not signed in'}
            </div>
          </div>
        </div>
      )}

      <div className="app-shell__sidebar-footer">
        {!isAuthenticated && (
          <p style={{ margin: '0 0 0.5rem' }}>
            <Link to="/login">
              {config?.auth_mode === 'free' ? 'Sign in (optional)' : 'Sign in'}
            </Link>
          </p>
        )}
        <div className="app-shell__sidebar-footer-row">
          <span>© {new Date().getFullYear()}</span>
          <span className="app-shell__sidebar-footer-sep">·</span>
          <a href={LICENSE} target="_blank" rel="noopener noreferrer">MIT</a>
          <span className="app-shell__sidebar-footer-sep">·</span>
          <a href={GITHUB_REPO} target="_blank" rel="noopener noreferrer">GitHub</a>
          <LegalFooterLinks legal={legal} />
        </div>
      </div>
    </aside>
  )
}
