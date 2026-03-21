import { useEffect, useState } from 'react'
import { apiFetch } from '../utils/apiClient'

interface ScannerRow {
  tools_key: string
  display_name: string
  standard_profile_timeout: number | null
  discovery_enabled: boolean
  effective_timeout: number
  effective_enabled: boolean
  db_override: {
    enabled: boolean | null
    timeout_seconds: number | null
    config: Record<string, string>
  } | null
}

export default function AdminScannerToolSettingsPage() {
  const [items, setItems] = useState<ScannerRow[]>([])
  const [help, setHelp] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<string | null>(null)
  const [formEnabled, setFormEnabled] = useState<boolean | null>(null)
  const [formTimeout, setFormTimeout] = useState<string>('')
  const [formSonarUrl, setFormSonarUrl] = useState('')
  const [formSonarToken, setFormSonarToken] = useState('')
  const [formSnykToken, setFormSnykToken] = useState('')
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch('/api/admin/scanner-tool-settings')
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setItems(data.scanners || [])
      setHelp(data.help || null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const openEdit = (row: ScannerRow) => {
    setEditing(row.tools_key)
    const db = row.db_override
    setFormEnabled(db?.enabled ?? null)
    setFormTimeout(db?.timeout_seconds != null ? String(db.timeout_seconds) : '')
    const c = db?.config || {}
    setFormSonarUrl(String(c.SONAR_HOST_URL || ''))
    setFormSonarToken(c.SONAR_TOKEN === '********' ? '' : String(c.SONAR_TOKEN || ''))
    setFormSnykToken(c.SNYK_TOKEN === '********' ? '' : String(c.SNYK_TOKEN || ''))
  }

  const save = async () => {
    if (!editing) return
    setSaving(true)
    setError(null)
    try {
      const body: Record<string, unknown> = {}
      if (formEnabled !== null) body.enabled = formEnabled
      if (formTimeout.trim()) {
        const t = parseInt(formTimeout, 10)
        if (t >= 30 && t <= 86400) body.timeout_seconds = t
      }
      const config: Record<string, string> = {}
      if (formSonarUrl.trim()) config.SONAR_HOST_URL = formSonarUrl.trim()
      if (formSonarToken.trim()) config.SONAR_TOKEN = formSonarToken.trim()
      if (formSnykToken.trim()) config.SNYK_TOKEN = formSnykToken.trim()
      if (Object.keys(config).length) body.config = config
      if (!Object.keys(body).length) {
        setError('Set at least one field')
        setSaving(false)
        return
      }
      const enc = encodeURIComponent(editing)
      const res = await apiFetch(`/api/admin/scanner-tool-settings/${enc}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await res.text())
      setEditing(null)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const clearOverrides = async (key: string) => {
    if (!confirm(`Clear all DB overrides for ${key}? Manifest defaults apply again.`)) return
    try {
      const enc = encodeURIComponent(key)
      const res = await apiFetch(`/api/admin/scanner-tool-settings/${enc}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  return (
    <div className="admin-dashboard-page" style={{ padding: '1.5rem', maxWidth: '960px' }}>
      <h1>Tool settings (DB overrides)</h1>
      <p style={{ opacity: 0.85, marginBottom: '1rem' }}>
        API path uses <strong>tools_key</strong> (slug: semgrep, sonarqube, …). Manifest = defaults; DB row keyed by
        tools_key only. Fresh DB: sync scanners first.
      </p>
      {help && (
        <pre style={{ fontSize: '0.8rem', opacity: 0.7, marginBottom: '1rem' }}>
          {JSON.stringify(help, null, 2)}
        </pre>
      )}
      {error && <p style={{ color: 'var(--error, #c00)' }}>{error}</p>}
      {loading ? (
        <p>Loading…</p>
      ) : (
        <table className="admin-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '0.5rem' }}>Tool / tools_key</th>
              <th style={{ textAlign: 'left' }}>standard profile (manifest)</th>
              <th style={{ textAlign: 'left' }}>Effective</th>
              <th style={{ textAlign: 'left' }}>DB override</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.tools_key} style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                <td style={{ padding: '0.5rem' }}>
                  <strong>{row.display_name}</strong>
                  <div style={{ fontSize: '0.75rem', opacity: 0.75, fontFamily: 'monospace' }}>{row.tools_key}</div>
                  {!row.discovery_enabled && (
                    <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem' }}>(discovery off)</span>
                  )}
                </td>
                <td>{row.standard_profile_timeout != null ? `${row.standard_profile_timeout}s` : '—'}</td>
                <td>
                  {row.effective_timeout}s / {row.effective_enabled ? 'on' : 'off'}
                </td>
                <td style={{ fontSize: '0.85rem' }}>
                  {row.db_override ? (
                    <code>{JSON.stringify(row.db_override)}</code>
                  ) : (
                    <em>none</em>
                  )}
                </td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  <button type="button" className="btn-secondary" onClick={() => openEdit(row)}>
                    Edit
                  </button>{' '}
                  {row.db_override && (
                    <button type="button" className="btn-secondary" onClick={() => clearOverrides(row.tools_key)}>
                      Clear DB
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {editing && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: 'var(--card-bg, #1a1a24)',
              padding: '1.5rem',
              borderRadius: '8px',
              minWidth: '320px',
              maxWidth: '90vw',
            }}
          >
            <h3 style={{ fontFamily: 'monospace' }}>{editing}</h3>
            <label style={{ display: 'block', marginTop: '0.75rem' }}>
              Force enabled
              <select
                value={formEnabled === null ? '' : formEnabled ? 'true' : 'false'}
                onChange={(e) =>
                  setFormEnabled(e.target.value === '' ? null : e.target.value === 'true')
                }
                style={{ marginLeft: '0.5rem' }}
              >
                <option value="">(use discovery)</option>
                <option value="true">enabled</option>
                <option value="false">disabled</option>
              </select>
            </label>
            <label style={{ display: 'block', marginTop: '0.75rem' }}>
              Timeout override (seconds, 30–86400)
              <input
                type="number"
                value={formTimeout}
                onChange={(e) => setFormTimeout(e.target.value)}
                placeholder="empty = manifest"
                style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
              />
            </label>
            <label style={{ display: 'block', marginTop: '0.75rem' }}>
              SONAR_HOST_URL
              <input
                value={formSonarUrl}
                onChange={(e) => setFormSonarUrl(e.target.value)}
                placeholder="https://sonar.company.com"
                style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
              />
            </label>
            <label style={{ display: 'block', marginTop: '0.75rem' }}>
              SONAR_TOKEN (leave empty to keep existing)
              <input
                type="password"
                value={formSonarToken}
                onChange={(e) => setFormSonarToken(e.target.value)}
                style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
              />
            </label>
            <label style={{ display: 'block', marginTop: '0.75rem' }}>
              SNYK_TOKEN
              <input
                type="password"
                value={formSnykToken}
                onChange={(e) => setFormSnykToken(e.target.value)}
                style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
              />
            </label>
            <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
              <button type="button" className="btn-primary" disabled={saving} onClick={save}>
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button type="button" className="btn-secondary" onClick={() => setEditing(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
