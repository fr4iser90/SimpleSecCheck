import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useConfig } from '../hooks/useConfig'
import ThemeToggle from '../components/ThemeToggle'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const { config } = useConfig()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await login(email, password, rememberMe)
      // Redirect to home after successful login
      navigate('/')
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.75rem' }}>
            <ThemeToggle />
          </div>
          <h1>🛡️ SimpleSecCheck</h1>
          <p>Please sign in to continue</p>
        </div>

        {error && (
          <div className="error-message" role="alert">
            {error}
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
              autoComplete="current-password"
              placeholder="••••••••"
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
              <span>Remember me</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={loading || !email || !password}
            className="login-button"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

          <div style={{ marginTop: '16px', textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <Link to="/password-reset" style={{ color: 'var(--accent)', textDecoration: 'none', fontSize: '14px' }}>
              Forgot password?
            </Link>
            {config?.features?.allow_self_registration && (
              <Link to="/signup" style={{ color: 'var(--accent)', textDecoration: 'none', fontSize: '14px' }}>
                Create an account
              </Link>
            )}
            <Link to="/capabilities" style={{ color: 'var(--accent)', textDecoration: 'none', fontSize: '14px' }}>
              Guest vs account (live config)
            </Link>
          </div>

          {config?.auth_mode === 'free' && (
            <div className="info-message">
              <p>Note: Authentication is currently set to "free" mode.</p>
              <p>Login is not required, but you can still sign in for additional features.</p>
            </div>
          )}
      </div>
    </div>
  )
}
