import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface CardItem {
  to: string
  title: string
  description: string
  icon: string
  comingSoon?: boolean
}

interface DashboardGroup {
  id: string
  title: string
  emoji: string
  cards: CardItem[]
}

/** Grouped admin areas: System, Users, Execution, Scan Engine, Security, Observability */
const DASHBOARD_GROUPS: DashboardGroup[] = [
  {
    id: 'system',
    title: 'System',
    emoji: '⚙️',
    cards: [
      {
        to: '/admin/settings',
        title: 'System Settings',
        description: 'SMTP and system email',
        icon: '📧',
      },
      {
        to: '/admin/auth',
        title: 'Auth Settings',
        description: 'Auth mode, guest access, self-registration',
        icon: '🔐',
      },
    ],
  },
  {
    id: 'users',
    title: 'Users',
    emoji: '👥',
    cards: [
      {
        to: '/admin/users',
        title: 'User Management',
        description: 'Users, roles, create, edit, delete',
        icon: '👤',
      },
      {
        to: '/admin/feature-flags',
        title: 'Feature Flags',
        description: 'Local paths, Git, ZIP, container, network scans',
        icon: '🚩',
      },
    ],
  },
  {
    id: 'execution',
    title: 'Execution',
    emoji: '🚦',
    cards: [
      {
        to: '/admin/execution',
        title: 'Queue & parallel scans',
        description: 'Max concurrent jobs, FIFO / priority / round-robin, role priorities',
        icon: '📊',
      },
      {
        to: '#',
        title: 'Rate limits',
        description: 'Global scan rate limits per tenant (planned)',
        icon: '⏱️',
        comingSoon: true,
      },
    ],
  },
  {
    id: 'scan-engine',
    title: 'Scan Engine',
    emoji: '🔧',
    cards: [
      {
        to: '/admin/scanner',
        title: 'Scanners & assets',
        description: 'Registry, worker, OWASP/Trivy caches, asset refresh',
        icon: '🔩',
      },
      {
        to: '/admin/tool-settings',
        title: 'Tool settings',
        description: 'DB + manifest overrides: timeouts, tokens, SonarQube, Snyk',
        icon: '🧩',
      },
      {
        to: '/admin/tool-duration',
        title: 'Tool duration',
        description: 'Measured run times per scanner for queue estimates',
        icon: '⏱️',
      },
    ],
  },
  {
    id: 'security',
    title: 'Security',
    emoji: '🔐',
    cards: [
      {
        to: '/admin/policies',
        title: 'Policies',
        description: 'Security rules & compliance (staging; enforcement later)',
        icon: '🔒',
      },
      {
        to: '/admin/security/ip-control',
        title: 'Abuse protection',
        description: 'Block IPs, abuse limits',
        icon: '🛡️',
      },
    ],
  },
  {
    id: 'observability',
    title: 'Observability',
    emoji: '🔭',
    cards: [
      {
        to: '/admin/audit-log',
        title: 'Audit Log',
        description: 'Security-relevant events and admin changes',
        icon: '📋',
      },
      {
        to: '/admin/health',
        title: 'System Health',
        description: 'Database, Redis, worker API status',
        icon: '❤️',
      },
    ],
  },
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
            System, execution, scan engine, security, and observability
          </p>
        </div>

        {DASHBOARD_GROUPS.map((group) => (
          <section key={group.id} className="admin-dashboard-section" aria-labelledby={`admin-section-${group.id}`}>
            <h2 id={`admin-section-${group.id}`} className="admin-dashboard-section-title">
              <span className="admin-dashboard-section-emoji" aria-hidden>
                {group.emoji}
              </span>
              {group.title}
            </h2>
            <div className="admin-dashboard-grid">
              {group.cards.map((item) => (
                <Link
                  key={`${group.id}-${item.title}`}
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
          </section>
        ))}
      </div>
    </div>
  )
}
