import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import { apiFetch } from '../utils/apiClient'
import './CapabilitiesPage.css'

interface RoleSnapshot {
  allowed_scan_targets: string[]
  my_targets: boolean
  bulk_scan: boolean
  scanner_access: string
}

interface CapabilitiesPayload {
  guest: RoleSnapshot
  user: RoleSnapshot
  auth: {
    allow_self_registration: boolean
    login_required: boolean
    access_mode: string
    auth_mode: string
  }
  help: string
}

function scannerLabel(access: string): string {
  return access === 'all_enabled' ? 'All enabled scanners on this instance' : 'Limited set (admin-configured)'
}

function TargetList({ items }: { items: string[] }) {
  if (!items.length) {
    return <span className="capabilities-page__empty">None enabled for this role on this instance</span>
  }
  return (
    <ul className="capabilities-page__list">
      {items.map((t) => (
        <li key={t}>{t}</li>
      ))}
    </ul>
  )
}

export default function CapabilitiesPage() {
  const [data, setData] = useState<CapabilitiesPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const r = await apiFetch('/api/config/capabilities', {}, false)
        const j = await r.json().catch(() => ({}))
        if (!r.ok) {
          setError(j.detail || 'Failed to load capabilities')
          return
        }
        setData(j)
      } catch {
        setError('Failed to load capabilities')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const rows = data
    ? [
        {
          label: 'Scan target types',
          guest: <TargetList items={data.guest.allowed_scan_targets} />,
          user: <TargetList items={data.user.allowed_scan_targets} />,
        },
        {
          label: 'My Targets',
          guest: data.guest.my_targets ? 'Yes' : 'No',
          user: data.user.my_targets ? 'Yes' : 'No',
        },
        {
          label: 'Bulk scan tab',
          guest: data.guest.bulk_scan ? 'Yes' : 'No',
          user: data.user.bulk_scan ? 'Yes' : 'No',
        },
        {
          label: 'Scanners',
          guest: scannerLabel(data.guest.scanner_access),
          user: scannerLabel(data.user.scanner_access),
        },
      ]
    : []

  return (
    <div className="container capabilities-page">
      <PageHeader
        title="Guest vs account"
        subtitle="What you get without signing in vs with an account — from the live server configuration."
      />

      {loading && <p className="capabilities-page__loading">Loading…</p>}
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {data && (
        <>
          <p className="capabilities-page__help">{data.help}</p>

          <div className="capabilities-page__table-wrap">
            <table className="capabilities-page__table">
              <thead>
                <tr>
                  <th scope="col">Capability</th>
                  <th scope="col">Guest (no account)</th>
                  <th scope="col">Signed-in user</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.label}>
                    <th scope="row">{row.label}</th>
                    <td>{row.guest}</td>
                    <td>{row.user}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="capabilities-page__cards" aria-label="Capability comparison">
            {rows.map((row) => (
              <article key={row.label} className="capabilities-page__card">
                <h2 className="capabilities-page__card-title">{row.label}</h2>
                <div className="capabilities-page__card-row">
                  <span className="capabilities-page__card-label">Guest</span>
                  <div className="capabilities-page__card-value">{row.guest}</div>
                </div>
                <div className="capabilities-page__card-row">
                  <span className="capabilities-page__card-label">Signed-in</span>
                  <div className="capabilities-page__card-value">{row.user}</div>
                </div>
              </article>
            ))}
          </div>

          <section className="capabilities-page__auth">
            <h2 className="capabilities-page__auth-title">Access &amp; registration</h2>
            <ul className="capabilities-page__auth-list">
              <li>
                Access mode: <strong>{data.auth.access_mode}</strong>
              </li>
              <li>
                Login required for scans: <strong>{data.auth.login_required ? 'Yes' : 'No'}</strong>
              </li>
              <li>
                Auth mode: <strong>{data.auth.auth_mode}</strong>
              </li>
              <li>
                Self-registration:{' '}
                <strong>{data.auth.allow_self_registration ? 'Open' : 'Admin-created accounts only'}</strong>
              </li>
            </ul>
          </section>

          <div className="capabilities-page__links">
            <Link to="/">← Home / Start scan</Link>
            <Link to="/login">Sign in</Link>
            {data.auth.allow_self_registration && <Link to="/signup">Create account</Link>}
          </div>
        </>
      )}
    </div>
  )
}
