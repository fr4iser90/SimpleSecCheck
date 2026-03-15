import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'

interface Profile {
  user_id: string
  email: string
  username: string
  role: string
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login: string | null
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  })
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const loadProfile = async () => {
    setLoading(true)
    try {
      const response = await apiFetch('/api/user/profile')
      if (response.ok) {
        const data = await response.json()
        setProfile(data)
      }
    } catch (error) {
      console.error('Failed to load profile:', error)
      setMessage({ type: 'error', text: 'Failed to load profile' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProfile()
  }, [])

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setMessage({ type: 'error', text: 'New passwords do not match' })
      return
    }

    if (passwordForm.new_password.length < 8) {
      setMessage({ type: 'error', text: 'Password must be at least 8 characters' })
      return
    }

    try {
      const response = await apiFetch('/api/user/profile/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password
        })
      })
      
      if (response.ok) {
        setMessage({ type: 'success', text: 'Password changed successfully' })
        setShowPasswordForm(false)
        setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
        setTimeout(() => setMessage(null), 3000)
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to change password' })
      }
    } catch (error) {
      console.error('Failed to change password:', error)
      setMessage({ type: 'error', text: 'Failed to change password' })
    }
  }

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1>Profile</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
          Manage your account information and preferences
        </p>
      </div>

      {message && (
        <div style={{
          padding: '1rem',
          marginBottom: '1.5rem',
          borderRadius: '8px',
          background: message.type === 'success' ? 'rgba(40, 167, 69, 0.2)' : 'rgba(220, 53, 69, 0.2)',
          border: `1px solid ${message.type === 'success' ? 'var(--color-pass)' : 'var(--color-critical)'}`,
          color: message.type === 'success' ? 'var(--color-pass)' : 'var(--color-critical)'
        }}>
          {message.text}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading...</div>
      ) : profile ? (
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          {/* Account Information */}
          <div style={{
            background: 'var(--glass-bg-dark)',
            padding: '2rem',
            borderRadius: '8px',
            border: '1px solid var(--glass-border-dark)'
          }}>
            <h2 style={{ marginTop: 0, marginBottom: '1.5rem' }}>Account Information</h2>
            <div style={{ display: 'grid', gap: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '1rem', borderBottom: '1px solid var(--glass-border-dark)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Email:</span>
                <strong>{profile.email}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '1rem', borderBottom: '1px solid var(--glass-border-dark)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Username:</span>
                <strong>{profile.username}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '1rem', borderBottom: '1px solid var(--glass-border-dark)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Role:</span>
                <span style={{
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  background: profile.role === 'admin' ? 'rgba(220, 53, 69, 0.2)' : 'rgba(40, 167, 69, 0.2)',
                  color: profile.role === 'admin' ? 'var(--color-critical)' : 'var(--color-pass)'
                }}>
                  {profile.role}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '1rem', borderBottom: '1px solid var(--glass-border-dark)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Account Created:</span>
                <span>{new Date(profile.created_at).toLocaleDateString()}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Last Login:</span>
                <span>{profile.last_login ? new Date(profile.last_login).toLocaleString() : 'Never'}</span>
              </div>
            </div>
          </div>

          {/* Password Management */}
          <div style={{
            background: 'var(--glass-bg-dark)',
            padding: '2rem',
            borderRadius: '8px',
            border: '1px solid var(--glass-border-dark)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ margin: 0 }}>Password Management</h2>
              {!showPasswordForm && (
                <button onClick={() => setShowPasswordForm(true)}>
                  Change Password
                </button>
              )}
            </div>

            {showPasswordForm && (
              <form onSubmit={handlePasswordChange}>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem' }}>Current Password</label>
                  <input
                    type="password"
                    required
                    value={passwordForm.current_password}
                    onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem' }}>New Password</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={passwordForm.new_password}
                    onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                    style={{ width: '100%' }}
                  />
                  <small style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    Must be at least 8 characters
                  </small>
                </div>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem' }}>Confirm New Password</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={passwordForm.confirm_password}
                    onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button type="submit" className="primary">Change Password</button>
                  <button type="button" onClick={() => {
                    setShowPasswordForm(false)
                    setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
                  }}>
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* Quick Links */}
          <div style={{
            background: 'var(--glass-bg-dark)',
            padding: '2rem',
            borderRadius: '8px',
            border: '1px solid var(--glass-border-dark)'
          }}>
            <h2 style={{ marginTop: 0, marginBottom: '1rem' }}>Quick Links</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <a href="/api-keys" style={{ color: 'var(--text-dark)', textDecoration: 'none' }}>
                → Manage API Keys
              </a>
              <a href="/my-repos" style={{ color: 'var(--text-dark)', textDecoration: 'none' }}>
                → My GitHub Repos
              </a>
              <a href="/my-scans" style={{ color: 'var(--text-dark)', textDecoration: 'none' }}>
                → My Scans
              </a>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
          Failed to load profile
        </div>
      )}
    </div>
  )
}
