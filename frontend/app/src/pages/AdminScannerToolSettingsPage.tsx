import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AdminPageShell from '../components/AdminPageShell'
import AdminPanel from '../components/AdminPanel'
import { useToast } from '../context/ToastContext'
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
  const toast = useToast()
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
      if (!res.ok) {
        const text = await res.text()
        let detail = text
        try {
          const parsed = JSON.parse(text) as { detail?: string }
          detail = parsed.detail || text
        } catch {
          /* plain text */
        }
        throw new Error(detail)
      }
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
      toast.success('Scanner tool settings saved')
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
      toast.success(`Cleared overrides for ${key}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  return (
    <AdminPageShell
      title="Tool settings (DB overrides)"
      subtitle="Override per-scanner timeouts, enablement, and API tokens stored in the database."
      calloutTitle="Quick reference"
      callout={
        <dl className="page-kv-list">
          <div>
            <dt>tools_key</dt>
            <dd>API slug for each scanner (semgrep, sonarqube, …). Manifest values are defaults.</dd>
          </div>
          <div>
            <dt>Overrides</dt>
            <dd>DB rows replace manifest defaults until cleared. Sync scanners after a fresh install.</dd>
          </div>
          <div>
            <dt>Workers</dt>
            <dd>Runtime status and queue: <Link to="/admin/scanner">Scan Engine</Link>.</dd>
          </div>
        </dl>
      }
      error={error}
      loading={loading}
    >
      {help && (
        <pre className="code-stream admin-tool-settings__help" style={{ marginBottom: '1rem', maxHeight: 120 }}>
          {JSON.stringify(help, null, 2)}
        </pre>
      )}

      <AdminPanel flush>
        <div className="desktop-only-table data-table-wrap data-table-wrap--wide">
          <table className="data-table">
            <thead>
              <tr>
                <th>Tool / tools_key</th>
                <th>standard profile (manifest)</th>
                <th>Effective</th>
                <th>DB override</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.tools_key}>
                  <td>
                    <strong>{row.display_name}</strong>
                    <div style={{ fontSize: '0.75rem', color: 'var(--ds-text-secondary)', fontFamily: 'monospace' }}>
                      {row.tools_key}
                    </div>
                    {!row.discovery_enabled && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--ds-text-secondary)' }}>(discovery off)</span>
                    )}
                  </td>
                  <td>{row.standard_profile_timeout != null ? `${row.standard_profile_timeout}s` : '—'}</td>
                  <td>
                    {row.effective_timeout}s / {row.effective_enabled ? 'on' : 'off'}
                  </td>
                  <td style={{ fontSize: '0.85rem' }}>
                    {row.db_override ? <code>{JSON.stringify(row.db_override)}</code> : <em>none</em>}
                  </td>
                  <td>
                    <div className="admin-page-actions">
                      <button type="button" className="btn-secondary" onClick={() => openEdit(row)}>
                        Edit
                      </button>
                      {row.db_override && (
                        <button type="button" className="btn-secondary" onClick={() => clearOverrides(row.tools_key)}>
                          Clear DB
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mobile-card-list" aria-label="Tool settings (mobile)">
          {items.map((row) => (
            <article key={row.tools_key} className="mobile-data-card">
              <h3 className="mobile-data-card__title">{row.display_name}</h3>
              <p className="mobile-data-card__subtitle">{row.tools_key}</p>
              <div className="mobile-data-card__grid">
                <div className="mobile-data-card__row">
                  <span className="mobile-data-card__label">Manifest</span>
                  <span className="mobile-data-card__value">
                    {row.standard_profile_timeout != null ? `${row.standard_profile_timeout}s` : '—'}
                  </span>
                </div>
                <div className="mobile-data-card__row">
                  <span className="mobile-data-card__label">Effective</span>
                  <span className="mobile-data-card__value">
                    {row.effective_timeout}s / {row.effective_enabled ? 'on' : 'off'}
                  </span>
                </div>
                <div className="mobile-data-card__row">
                  <span className="mobile-data-card__label">DB override</span>
                  <span className="mobile-data-card__value">
                    {row.db_override ? 'yes' : 'none'}
                  </span>
                </div>
              </div>
              <div className="mobile-data-card__actions">
                <button type="button" className="btn-secondary" onClick={() => openEdit(row)}>
                  Edit
                </button>
                {row.db_override ? (
                  <button type="button" className="btn-secondary" onClick={() => clearOverrides(row.tools_key)}>
                    Clear DB
                  </button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </AdminPanel>

      {editing && (
        <div className="ui-modal-overlay">
          <div className="ui-modal" style={{ maxWidth: 420 }}>
            <h3 className="ui-modal__title" style={{ fontFamily: 'monospace' }}>
              {editing}
            </h3>
            <div className="form-group">
              <label>Force enabled</label>
              <select
                value={formEnabled === null ? '' : formEnabled ? 'true' : 'false'}
                onChange={(e) =>
                  setFormEnabled(e.target.value === '' ? null : e.target.value === 'true')
                }
              >
                <option value="">(use discovery)</option>
                <option value="true">enabled</option>
                <option value="false">disabled</option>
              </select>
            </div>
            <div className="form-group">
              <label>Timeout override (seconds, 30–86400)</label>
              <input
                type="number"
                value={formTimeout}
                onChange={(e) => setFormTimeout(e.target.value)}
                placeholder="empty = manifest"
              />
            </div>
            <div className="form-group">
              <label>SONAR_HOST_URL</label>
              <input
                value={formSonarUrl}
                onChange={(e) => setFormSonarUrl(e.target.value)}
                placeholder="https://sonar.company.com"
              />
            </div>
            <div className="form-group">
              <label>SONAR_TOKEN (leave empty to keep existing)</label>
              <input
                type="password"
                value={formSonarToken}
                onChange={(e) => setFormSonarToken(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>SNYK_TOKEN</label>
              <input type="password" value={formSnykToken} onChange={(e) => setFormSnykToken(e.target.value)} />
            </div>
            <div className="ui-modal__actions">
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
    </AdminPageShell>
  )
}
