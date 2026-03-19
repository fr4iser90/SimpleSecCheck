import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../utils/apiClient'

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

function Row({ label, guest, user }: { label: string; guest: React.ReactNode; user: React.ReactNode }) {
  return (
    <tr style={{ borderBottom: '1px solid var(--glass-border-dark)' }}>
      <th style={{ padding: '0.85rem 1rem', textAlign: 'left', verticalAlign: 'top', width: '28%' }}>{label}</th>
      <td style={{ padding: '0.85rem 1rem', verticalAlign: 'top' }}>{guest}</td>
      <td style={{ padding: '0.85rem 1rem', verticalAlign: 'top' }}>{user}</td>
    </tr>
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

  const scannerLabel = (access: string) =>
    access === 'all_enabled' ? 'All enabled scanners on this instance' : 'Limited set (admin-configured)'

  return (
    <div className="container" style={{ padding: '2rem', maxWidth: '960px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '0.5rem' }}>Guest vs account</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
        What you get without signing in vs with an account — from the live server configuration.
      </p>

      {loading && <p>Loading…</p>}
      {error && <div className="error-message" role="alert">{error}</div>}

      {data && (
        <>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
            {data.help}
          </p>

          <div style={{
            background: 'var(--glass-bg-dark)',
            borderRadius: '8px',
            border: '1px solid var(--glass-border-dark)',
            overflow: 'auto',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'rgba(255,255,255,0.05)' }}>
                  <th style={{ padding: '1rem', textAlign: 'left' }}>Capability</th>
                  <th style={{ padding: '1rem', textAlign: 'left' }}>Guest (no account)</th>
                  <th style={{ padding: '1rem', textAlign: 'left' }}>Signed-in user</th>
                </tr>
              </thead>
              <tbody>
                <Row
                  label="Scan target types"
                  guest={
                    data.guest.allowed_scan_targets.length ? (
                      <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
                        {data.guest.allowed_scan_targets.map((t) => (
                          <li key={t}>{t}</li>
                        ))}
                      </ul>
                    ) : (
                      <span style={{ opacity: 0.75 }}>None enabled for this role on this instance</span>
                    )
                  }
                  user={
                    data.user.allowed_scan_targets.length ? (
                      <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
                        {data.user.allowed_scan_targets.map((t) => (
                          <li key={t}>{t}</li>
                        ))}
                      </ul>
                    ) : (
                      <span style={{ opacity: 0.75 }}>None enabled for this role on this instance</span>
                    )
                  }
                />
                <Row
                  label="My Targets"
                  guest={data.guest.my_targets ? 'Yes' : 'No'}
                  user={data.user.my_targets ? 'Yes' : 'No'}
                />
                <Row
                  label="Bulk scan tab"
                  guest={data.guest.bulk_scan ? 'Yes' : 'No'}
                  user={data.user.bulk_scan ? 'Yes' : 'No'}
                />
                <Row
                  label="Scanners"
                  guest={scannerLabel(data.guest.scanner_access)}
                  user={scannerLabel(data.user.scanner_access)}
                />
              </tbody>
            </table>
          </div>

          <h2 style={{ marginTop: '2rem', marginBottom: '0.75rem', fontSize: '1.1rem' }}>Access &amp; registration</h2>
          <ul style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            <li>Access mode: <strong style={{ color: 'var(--text-dark)' }}>{data.auth.access_mode}</strong></li>
            <li>Login required for scans: <strong style={{ color: 'var(--text-dark)' }}>{data.auth.login_required ? 'Yes' : 'No'}</strong></li>
            <li>Auth mode: <strong style={{ color: 'var(--text-dark)' }}>{data.auth.auth_mode}</strong></li>
            <li>Self-registration: <strong style={{ color: 'var(--text-dark)' }}>{data.auth.allow_self_registration ? 'Open' : 'Admin-created accounts only'}</strong></li>
          </ul>

          <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <Link to="/" style={{ color: 'var(--color-primary)' }}>← Home / Start scan</Link>
            <Link to="/login" style={{ color: 'var(--color-primary)' }}>Sign in</Link>
            {data.auth.allow_self_registration && (
              <Link to="/signup" style={{ color: 'var(--color-primary)' }}>Create account</Link>
            )}
          </div>
        </>
      )}
    </div>
  )
}
