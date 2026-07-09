import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import AdminPageShell from '../components/AdminPageShell'
import { apiFetch } from '../utils/apiClient'

interface SMTPConfig {
  enabled: boolean
  host: string
  port: number
  user: string
  password: string
  use_tls: boolean
  from_email: string
  from_name: string
}

export default function AdminSettingsPage() {
  const [smtpConfig, setSmtpConfig] = useState<SMTPConfig>({
    enabled: false,
    host: 'smtp.gmail.com',
    port: 587,
    user: '',
    password: '',
    use_tls: true,
    from_email: 'noreply@simpleseccheck.local',
    from_name: 'SimpleSecCheck',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    void loadSMTPConfig()
  }, [])

  const loadSMTPConfig = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiFetch('/api/admin/config/smtp')
      if (!response.ok) throw new Error('Failed to load SMTP configuration')
      const data = await response.json()
      setSmtpConfig(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load SMTP configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleSMTPChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target
    setSmtpConfig({
      ...smtpConfig,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseInt(value, 10) : value,
    })
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      const response = await apiFetch('/api/admin/config/smtp', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(smtpConfig),
      })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Save failed' }))
        throw new Error(errorData.detail || 'Failed to save SMTP configuration')
      }
      setSuccess('SMTP configuration saved. Service restart may be required.')
      await loadSMTPConfig()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save SMTP configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleTestEmail = async () => {
    setError(null)
    setSuccess('Test email functionality coming soon')
  }

  return (
    <AdminPageShell
      title="System settings"
      subtitle="Outbound email for password reset, verification, and notifications."
      calloutTitle="Quick reference"
      callout={
        <dl className="page-kv-list">
          <div>
            <dt>SMTP</dt>
            <dd>Required when email verification or password reset is enabled.</dd>
          </div>
          <div>
            <dt>Related</dt>
            <dd>
              <Link to="/admin/auth">Auth settings</Link> · <Link to="/admin/execution">Execution</Link> ·{' '}
              <Link to="/admin/feature-flags">Feature flags</Link> · <Link to="/admin/health">Health</Link>
            </dd>
          </div>
        </dl>
      }
      error={error}
      success={success}
      loading={loading}
      loadingText="Loading settings…"
    >
      <div className="admin-settings-container">
        <form onSubmit={handleSave} className="settings-form">
          <div className="settings-section">
            <h3>SMTP email</h3>
            <p className="settings-section__lead">Password reset emails and system notifications.</p>

            <div className="form-group">
              <label className="form-check">
                <input type="checkbox" name="enabled" checked={smtpConfig.enabled} onChange={handleSMTPChange} />
                <span>Enable SMTP email</span>
              </label>
            </div>

            {smtpConfig.enabled && (
              <>
                <div className="form-field-row">
                  <div className="form-group">
                    <label htmlFor="smtp-host">SMTP host</label>
                    <input id="smtp-host" type="text" name="host" value={smtpConfig.host} onChange={handleSMTPChange} required />
                  </div>
                  <div className="form-group">
                    <label htmlFor="smtp-port">SMTP port</label>
                    <input id="smtp-port" type="number" name="port" value={smtpConfig.port} onChange={handleSMTPChange} required min={1} max={65535} />
                  </div>
                </div>
                <div className="form-group">
                  <label htmlFor="smtp-user">SMTP username / email</label>
                  <input id="smtp-user" type="email" name="user" value={smtpConfig.user} onChange={handleSMTPChange} required />
                </div>
                <div className="form-group">
                  <label htmlFor="smtp-password">SMTP password</label>
                  <input
                    id="smtp-password"
                    type="password"
                    name="password"
                    value={smtpConfig.password === '***' ? '' : smtpConfig.password}
                    onChange={handleSMTPChange}
                    placeholder={smtpConfig.password === '***' ? 'Leave empty to keep current password' : undefined}
                  />
                </div>
                <div className="form-group">
                  <label className="form-check">
                    <input type="checkbox" name="use_tls" checked={smtpConfig.use_tls} onChange={handleSMTPChange} />
                    <span>Use TLS</span>
                  </label>
                </div>
                <div className="form-field-row">
                  <div className="form-group">
                    <label htmlFor="smtp-from-email">From email</label>
                    <input id="smtp-from-email" type="email" name="from_email" value={smtpConfig.from_email} onChange={handleSMTPChange} required />
                  </div>
                  <div className="form-group">
                    <label htmlFor="smtp-from-name">From name</label>
                    <input id="smtp-from-name" type="text" name="from_name" value={smtpConfig.from_name} onChange={handleSMTPChange} required />
                  </div>
                </div>
              </>
            )}

            <div className="form-actions">
              {smtpConfig.enabled && (
                <button type="button" onClick={handleTestEmail} className="btn-secondary" disabled={saving}>
                  Test email
                </button>
              )}
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? 'Saving…' : 'Save configuration'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </AdminPageShell>
  )
}
