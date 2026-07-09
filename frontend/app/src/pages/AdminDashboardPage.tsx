import { Link } from 'react-router-dom'
import AppIcon from '../components/AppIcon'
import PageHeader from '../components/PageHeader'

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
  cards: CardItem[]
}

const DASHBOARD_GROUPS: DashboardGroup[] = [
  {
    id: 'system',
    title: 'System',
    cards: [
      { to: '/admin/settings', title: 'System Settings', description: 'SMTP and system email', icon: 'mail' },
      { to: '/admin/legal', title: 'Legal & Compliance', description: 'Impressum, privacy, cookie notice', icon: 'info' },
      { to: '/admin/auth', title: 'Auth Settings', description: 'Auth mode, guest access, registration', icon: 'lock' },
    ],
  },
  {
    id: 'users',
    title: 'Users',
    cards: [
      { to: '/admin/users', title: 'User Management', description: 'Users, roles, create, edit, delete', icon: 'users' },
      { to: '/admin/feature-flags', title: 'Feature Flags', description: 'Local paths, Git, ZIP, container, network', icon: 'flag' },
    ],
  },
  {
    id: 'execution',
    title: 'Execution',
    cards: [
      {
        to: '/admin/execution',
        title: 'Queue & parallel scans',
        description: 'Concurrency, rate limits, queue strategy',
        icon: 'queue',
      },
    ],
  },
  {
    id: 'scan-engine',
    title: 'Scan Engine',
    cards: [
      { to: '/admin/scanner', title: 'Scanners & assets', description: 'Registry, worker, asset refresh', icon: 'scan' },
      { to: '/admin/tool-settings', title: 'Tool settings', description: 'DB overrides: timeouts, tokens, SonarQube', icon: 'settings' },
      { to: '/admin/tool-duration', title: 'Tool duration', description: 'Measured run times for queue estimates', icon: 'clock' },
    ],
  },
  {
    id: 'security',
    title: 'Security',
    cards: [
      { to: '/admin/policies', title: 'Policies', description: 'Security rules and compliance staging', icon: 'shield' },
      { to: '/admin/security/ip-control', title: 'Abuse protection', description: 'Block IPs and abuse limits', icon: 'lock' },
    ],
  },
  {
    id: 'observability',
    title: 'Observability',
    cards: [
      { to: '/admin/audit-log', title: 'Audit Log', description: 'Security events and admin changes', icon: 'history' },
      { to: '/admin/health', title: 'System Health', description: 'Database, Redis, worker API status', icon: 'activity' },
      { to: '/admin/sse-debug', title: 'Live SSE', description: 'Debug stream for your session', icon: 'chart' },
    ],
  },
]

export default function AdminDashboardPage() {
  return (
    <div className="container">
      <PageHeader
        title="Admin"
        subtitle="System, execution, scan engine, security, and observability."
      />

      {DASHBOARD_GROUPS.map((group) => (
        <section key={group.id} className="admin-section" aria-labelledby={`admin-section-${group.id}`}>
          <h2 id={`admin-section-${group.id}`} className="admin-section__title">
            {group.title}
          </h2>
          <div className="admin-grid">
            {group.cards.map((item) => (
              <Link
                key={`${group.id}-${item.title}`}
                to={item.comingSoon ? '#' : item.to}
                className={`admin-tile ${item.comingSoon ? 'admin-tile--disabled' : ''}`}
                onClick={item.comingSoon ? (e) => e.preventDefault() : undefined}
              >
                <span className="admin-tile__icon">
                  <AppIcon name={item.icon} size={16} />
                </span>
                <h3 className="admin-tile__title">{item.title}</h3>
                <p className="admin-tile__desc">{item.description}</p>
                {item.comingSoon ? <span className="admin-tile__badge">Coming soon</span> : null}
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
