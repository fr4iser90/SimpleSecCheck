import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
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
  const { isAuthenticated } = useAuth()
  const [smtpConfig, setSmtpConfig] = useState<SMTPConfig>({
    enabled: false,
    host: 'smtp.gmail.com',
    port: 587,
    user: '',
    password: '',
    use_tls: true,
    from_email: 'noreply@simpleseccheck.local',
    from_name: 'SimpleSecCheck'
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated) {
      return
    }
    loadSMTPConfig()
  }, [isAuthenticated])

  const loadSMTPConfig = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await apiFetch('/api/admin/config/smtp')
      if (!response.ok) {
        throw new Error('Failed to load SMTP configuration')
      }
      
      const data = await response.json()
      setSmtpConfig(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load SMTP configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleSMTPChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target
    setSmtpConfig({
      ...smtpConfig,
      [name]: type === 'checkbox' ? checked : (type === 'number' ? parseInt(value) : value)
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
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(smtpConfig)
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Save failed' }))
        throw new Error(errorData.detail || 'Failed to save SMTP configuration')
      }

      setSuccess('SMTP configuration saved successfully. Service restart may be required for changes to take effect.')
      
      // Reload config to get masked password
      await loadSMTPConfig()
    } catch (err: any) {
      setError(err.message || 'Failed to save SMTP configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleTestEmail = async () => {
    // TODO: Implement test email sending
    setError(null)
    setSuccess('Test email functionality coming soon')
  }

  if (!isAuthenticated) {
    return (
      <div className="admin-settings-page">
        <div className="admin-settings-container">
          <h2>Access Denied</h2>
          <p>You must be logged in as an admin to access this page.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="admin-settings-page">
        <div className="admin-settings-container">
          <div className="loading">Loading settings...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-settings-page">
      <div className="admin-settings-container">
        <h2>System settings</h2>
        <p className="section-description" style={{ marginBottom: '1.25rem' }}>
          Email delivery below. Other global controls:{' '}
          <Link to="/admin/auth">Auth</Link>
          {' · '}
          <Link to="/admin/execution">Execution</Link> (parallel scans &amp; queue)
          {' · '}
          <Link to="/admin/feature-flags">Feature flags</Link>
          {' · '}
          <Link to="/admin/health">System health</Link>.
        </p>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        {success && (
          <div className="success-message" role="alert">
            {success}
          </div>
        )}

        <form onSubmit={handleSave} className="settings-form">
          <div className="settings-section">
            <h3>SMTP Email Configuration</h3>
            <p className="section-description">
              Configure SMTP settings to enable password reset emails and notifications.
            </p>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="enabled"
                  checked={smtpConfig.enabled}
                  onChange={handleSMTPChange}
                  style={{ cursor: 'pointer' }}
                />
                <span>Enable SMTP Email</span>
              </label>
            </div>

            {smtpConfig.enabled && (
              <>
                <div className="form-group">
                  <label>SMTP Host</label>
                  <input
                    type="text"
                    name="host"
                    value={smtpConfig.host}
                    onChange={handleSMTPChange}
                    placeholder="smtp.gmail.com"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>SMTP Port</label>
                  <input
                    type="number"
                    name="port"
                    value={smtpConfig.port}
                    onChange={handleSMTPChange}
                    placeholder="587"
                    min="1"
                    max="65535"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>SMTP Username/Email</label>
                  <input
                    type="email"
                    name="user"
                    value={smtpConfig.user}
                    onChange={handleSMTPChange}
                    placeholder="your@email.com"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>SMTP Password</label>
                  <input
                    type="password"
                    name="password"
                    value={smtpConfig.password === '***' ? '' : smtpConfig.password}
                    onChange={handleSMTPChange}
                    placeholder={smtpConfig.password === '***' ? 'Enter new password or leave empty to keep current' : 'SMTP password or app password'}
                  />
                  {smtpConfig.password === '***' && (
                    <small style={{ color: '#666', marginTop: '4px', display: 'block' }}>
                      Leave empty to keep current password, or enter new password
                    </small>
                  )}
                </div>

                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      name="use_tls"
                      checked={smtpConfig.use_tls}
                      onChange={handleSMTPChange}
                      style={{ cursor: 'pointer' }}
                    />
                    <span>Use TLS</span>
                  </label>
                </div>

                <div className="form-group">
                  <label>From Email</label>
                  <input
                    type="email"
                    name="from_email"
                    value={smtpConfig.from_email}
                    onChange={handleSMTPChange}
                    placeholder="noreply@simpleseccheck.local"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>From Name</label>
                  <input
                    type="text"
                    name="from_name"
                    value={smtpConfig.from_name}
                    onChange={handleSMTPChange}
                    placeholder="SimpleSecCheck"
                    required
                  />
                </div>

                <div className="form-actions">
                  <button
                    type="button"
                    onClick={handleTestEmail}
                    className="btn-secondary"
                    disabled={saving}
                  >
                    Test Email
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={saving}
                  >
                    {saving ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              </>
            )}

            {!smtpConfig.enabled && (
              <div className="form-actions">
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save Configuration'}
                </button>
              </div>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
