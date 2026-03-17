import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { apiFetch } from '../utils/apiClient'

interface AuthConfig {
  auth_mode: 'free' | 'basic' | 'jwt'
  access_mode: 'public' | 'mixed' | 'private'
  allow_self_registration: boolean
  bulk_scan_allow_guests?: boolean
}

export default function AuthSettingsPage() {
  const { isAuthenticated, user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [config, setConfig] = useState<AuthConfig>({
    auth_mode: 'free',
    access_mode: 'public',
    allow_self_registration: false,
    bulk_scan_allow_guests: false
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated) return
    loadAuthConfig()
  }, [isAuthenticated])

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

  if (!isAuthenticated || !isAdmin) {
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
          <div className="loading">Loading auth configuration...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-settings-page">
      <div className="admin-settings-container">
        <h2>Auth Settings</h2>
        <p className="section-description" style={{ marginBottom: '1.5rem' }}>
          AUTH_MODE = how users log in. ACCESS_MODE = who may use the system (public / mixed / private). Self-registration is separate. Not Feature Flags (those control scan targets).
        </p>
        {error && <div className="error-message" role="alert">{error}</div>}
        {success && <div className="success-message" role="alert">{success}</div>}
        <form onSubmit={handleSave} className="settings-form">
          <div className="settings-section">
            <h3>Login mechanism (AUTH_MODE)</h3>
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
              <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                Only defines the mechanism. Who may access is controlled by Access mode below.
              </small>
            </div>
          </div>
          <div className="settings-section">
            <h3>Who may use the system (ACCESS_MODE)</h3>
            <div className="form-group">
              <label htmlFor="access_mode">Access mode</label>
              <select
                id="access_mode"
                name="access_mode"
                value={config.access_mode}
                onChange={handleChange}
              >
                <option value="public">Public — All areas open (no login required)</option>
                <option value="mixed">Mixed — Scan, queue, stats public; dashboard / profile require login</option>
                <option value="private">Private — Login required for scans, queue, stats, and everything else</option>
              </select>
              <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                Public/Mixed = guests can start scans. Private = only logged-in users.
              </small>
            </div>
          </div>
          <div className="settings-section">
            <h3>Registration</h3>
            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="allow_self_registration"
                  checked={config.allow_self_registration}
                  onChange={handleChange}
                  style={{ cursor: 'pointer' }}
                />
                Allow self-registration (sign up)
              </label>
              <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                Users can create their own account. If off, only admins can create users. Requires SMTP for verification/password reset if you use email verification later.
              </small>
            </div>
          </div>
          <div className="settings-section">
            <h3>Bulk scan (override)</h3>
            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="bulk_scan_allow_guests"
                  checked={config.bulk_scan_allow_guests ?? false}
                  onChange={handleChange}
                  style={{ cursor: 'pointer' }}
                />
                Allow guest bulk scan
              </label>
              <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                By default only logged-in users can use the bulk scan tab. Enable this to allow guests to use bulk scan as well.
              </small>
            </div>
          </div>
          <div style={{ marginTop: '1.5rem' }}>
            <button type="submit" className="primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save auth configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
