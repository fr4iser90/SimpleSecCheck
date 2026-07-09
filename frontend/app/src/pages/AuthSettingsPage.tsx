import { useState, useEffect } from 'react'
import AdminPageShell from '../components/AdminPageShell'
import { apiFetch } from '../utils/apiClient'

interface AuthConfig {
  auth_mode: 'free' | 'basic' | 'jwt'
  access_mode: 'public' | 'mixed' | 'private'
  allow_self_registration: boolean
  registration_approval?: 'auto' | 'admin_approval'
  require_email_verification?: boolean
  bulk_scan_allow_guests?: boolean
}

export default function AuthSettingsPage() {
  const [config, setConfig] = useState<AuthConfig>({
    auth_mode: 'free',
    access_mode: 'public',
    allow_self_registration: false,
    registration_approval: 'auto',
    require_email_verification: false,
    bulk_scan_allow_guests: false
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    void loadAuthConfig()
  }, [])

  const loadAuthConfig = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiFetch('/api/admin/config/auth')
      if (!response.ok) throw new Error('Failed to load auth configuration')
      const data = await response.json()
      setConfig(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load auth configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) => {
    const { name, value, type } = e.target
    setConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }))
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      const response = await apiFetch('/api/admin/config/auth', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to save auth configuration')
      }
      setSuccess('Auth configuration saved successfully.')
      await loadAuthConfig()
    } catch (err: any) {
      setError(err.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AdminPageShell
      title="Auth settings"
      subtitle="Control how users sign in, who may use the app without an account, and registration rules."
      calloutTitle="Quick reference"
      callout={
        <dl className="page-kv-list">
          <div>
            <dt>AUTH_MODE</dt>
            <dd>Login mechanism — free (no accounts), basic (password), or JWT.</dd>
          </div>
          <div>
            <dt>ACCESS_MODE</dt>
            <dd>Who may use scans and insights — public, mixed, or private.</dd>
          </div>
          <div>
            <dt>Feature flags</dt>
            <dd>Separate setting — controls which scan targets are allowed.</dd>
          </div>
        </dl>
      }
      error={error}
      success={success}
      loading={loading}
      loadingText="Loading auth configuration…"
    >
      <div className="admin-settings-container">
        <form onSubmit={handleSave} className="settings-form">
          <div className="settings-section">
            <h3>Login mechanism</h3>
            <p className="settings-section__lead">AUTH_MODE — defines how users authenticate.</p>
            <div className="form-group">
              <label htmlFor="auth_mode">How users log in</label>
              <select
                id="auth_mode"
                name="auth_mode"
                value={config.auth_mode}
                onChange={handleChange}
              >
                <option value="free">Free — No login (no accounts)</option>
                <option value="basic">Basic — Username/password</option>
                <option value="jwt">JWT — Token / SSO</option>
              </select>
              <p className="form-help-text">
                Only defines the mechanism. Who may access is controlled by access mode below.
              </p>
            </div>
          </div>

          <div className="settings-section">
            <h3>Access mode</h3>
            <p className="settings-section__lead">ACCESS_MODE — who may use the system without signing in.</p>
            <div className="form-group">
              <label htmlFor="access_mode">Access mode</label>
              <select
                id="access_mode"
                name="access_mode"
                value={config.access_mode}
                onChange={handleChange}
              >
                <option value="public">Public — All areas open (no login required)</option>
                <option value="mixed">Mixed — Scan, queue, stats public; profile requires login</option>
                <option value="private">Private — Login required everywhere</option>
              </select>
              <p className="form-help-text">
                Public and mixed allow guests to start scans. Private requires a signed-in user.
              </p>
            </div>
          </div>

          <div className="settings-section">
            <h3>Registration</h3>
            <p className="settings-section__lead">Self-service sign-up and email verification.</p>
            <div className="form-group">
              <label className="form-check">
                <input
                  type="checkbox"
                  name="allow_self_registration"
                  checked={config.allow_self_registration}
                  onChange={handleChange}
                />
                <span>Allow self-registration (sign up)</span>
              </label>
              <p className="form-help-text">
                When off, only admins can create users. SMTP is used for password reset and verification emails.
              </p>
            </div>
            {config.allow_self_registration && (
              <div className="form-group">
                <label htmlFor="registration_approval">New user approval</label>
                <select
                  id="registration_approval"
                  name="registration_approval"
                  value={config.registration_approval ?? 'auto'}
                  onChange={handleChange}
                >
                  <option value="auto">Auto accept — users can log in immediately</option>
                  <option value="admin_approval">Admin approval — pending until you activate them</option>
                </select>
                <p className="form-help-text">
                  Pending users appear under User Management until you accept them.
                </p>
              </div>
            )}
            <div className="form-group">
              <label className="form-check">
                <input
                  type="checkbox"
                  name="require_email_verification"
                  checked={config.require_email_verification ?? false}
                  onChange={handleChange}
                />
                <span>Require email verification before login</span>
              </label>
              <p className="form-help-text">
                Requires SMTP so verification emails can be sent after sign-up.
              </p>
            </div>
          </div>

          <div className="settings-section">
            <h3>Bulk scan</h3>
            <p className="settings-section__lead">Optional override for the bulk-scan tab on the home page.</p>
            <div className="form-group">
              <label className="form-check">
                <input
                  type="checkbox"
                  name="bulk_scan_allow_guests"
                  checked={config.bulk_scan_allow_guests ?? false}
                  onChange={handleChange}
                />
                <span>Allow guest bulk scan</span>
              </label>
              <p className="form-help-text">
                By default only logged-in users can use bulk scan. Enable to allow guests as well.
              </p>
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save auth configuration'}
            </button>
          </div>
        </form>
      </div>
    </AdminPageShell>
  )
}
