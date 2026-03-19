import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useConfig } from '../hooks/useConfig'
import { apiFetch } from '../utils/apiClient'

export default function SignUpPage() {
  const navigate = useNavigate()
  const { config } = useConfig()
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setLoading(true)
    try {
      const response = await apiFetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, username, password }),
      }, false)
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        setError(data.detail || 'Registration failed')
        return
      }
      const parts = [
        data.requires_approval
          ? 'Account created. An administrator must approve your account before you can log in.'
          : 'Account created. You can now sign in.',
      ]
      if (data.verification_email_sent) {
        parts.push(' Check your email and click the verification link to verify your address.')
      }
      setSuccess(parts.join(''))
      if (!data.requires_approval) {
        setTimeout(() => navigate('/login'), 2000)
      }
    } catch (err: any) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  if (config && !config.features?.allow_self_registration) {
    return (
      <div className="login-page">
        <div className="login-container">
          <h1>🛡️ SimpleSecCheck</h1>
          <p>Self-registration is disabled. Contact an administrator to get an account.</p>
          <Link to="/login" style={{ color: 'var(--color-primary)', marginTop: '1rem', display: 'inline-block' }}>
            ← Back to Sign in
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>🛡️ SimpleSecCheck</h1>
          <p>Create an account</p>
        </div>

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

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="your@email.com"
              disabled={!!success}
            />
          </div>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={2}
              maxLength={100}
              autoComplete="username"
              placeholder="username"
              disabled={!!success}
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              placeholder="••••••••"
              disabled={!!success}
            />
            <small style={{ display: 'block', marginTop: '0.25rem', color: 'var(--text-secondary)' }}>
              At least 8 characters
            </small>
          </div>

          <button
            type="submit"
            disabled={loading || !!success}
            className="login-button"
          >
            {loading ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>

        <div style={{ marginTop: '16px', textAlign: 'center' }}>
          <Link to="/login" style={{ color: 'var(--color-primary)', textDecoration: 'none', fontSize: '14px' }}>
            Already have an account? Sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
