import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface CardItem {
  to: string
  title: string
  description: string
  icon: string
  comingSoon?: boolean
}

const adminSections: CardItem[] = [
  { to: '/admin/settings', title: 'System Settings', description: 'SMTP, security mode, scanner config', icon: '⚙️' },
  { to: '/admin/auth', title: 'Auth Settings', description: 'Auth mode, guest access, self-registration', icon: '🔐' },
  { to: '/admin/queue', title: 'Queue & Scan Order', description: 'Queue strategy: FIFO, priority, or round-robin', icon: '📊' },
  { to: '/admin/users', title: 'User Management', description: 'Users, roles, create, edit, delete', icon: '👥' },
  { to: '/admin/feature-flags', title: 'Feature Flags', description: 'Allow local paths, Git, ZIP, container, network scans', icon: '🚩' },
  { to: '/admin/security', title: 'Security Policies', description: 'Use cases, rate limits', icon: '🔒', comingSoon: true },
  { to: '/admin/audit-log', title: 'Audit Log', description: 'Security-relevant events and changes', icon: '📋' },
  { to: '/admin/security/ip-control', title: 'IP & Abuse Protection', description: 'Block IPs, abuse limits', icon: '🛡️' },
  { to: '/admin/scanner', title: 'Scan Engine Management', description: 'Scanners, assets, updates', icon: '🔧' },
  { to: '/admin/vulnerabilities', title: 'Vulnerability Database', description: 'CVE data, updates', icon: '📦', comingSoon: true },
  { to: '/admin/scan-policies', title: 'Scan Policies', description: 'Finding policies, rules', icon: '📜', comingSoon: true },
  { to: '/admin/notifications', title: 'Notification Management', description: 'Alerts, webhooks', icon: '🔔', comingSoon: true },
  { to: '/admin/health', title: 'System Health', description: 'Database, Redis, resources, metrics', icon: '❤️', comingSoon: true },
]

export default function AdminDashboardPage() {
  const { isAuthenticated, user } = useAuth()
  const isAdmin = user?.role === 'admin'

  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="admin-dashboard-page">
        <div className="admin-dashboard-container">
          <h2>Access Denied</h2>
          <p>You must be logged in as an admin to access the admin area.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-dashboard-page">
      <div className="admin-dashboard-container">
        <div className="admin-dashboard-header">
          <h1>Admin Dashboard</h1>
          <p className="admin-dashboard-subtitle">
            System configuration, users, feature flags, and security
          </p>
        </div>

        <div className="admin-dashboard-grid">
          {adminSections.map((item) => (
            <Link
              key={item.to}
              to={item.comingSoon ? '#' : item.to}
              className={`admin-dashboard-card ${item.comingSoon ? 'admin-dashboard-card--disabled' : ''}`}
              onClick={item.comingSoon ? (e) => e.preventDefault() : undefined}
              style={item.comingSoon ? { cursor: 'default' } : undefined}
            >
              <span className="admin-dashboard-card-icon">{item.icon}</span>
              <h3 className="admin-dashboard-card-title">{item.title}</h3>
              <p className="admin-dashboard-card-description">{item.description}</p>
              {item.comingSoon && (
                <span className="admin-dashboard-card-badge">Coming Soon</span>
              )}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
