import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import './PasswordResetPage.css'

export default function PasswordResetPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  
  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      const { apiFetch } = await import('../utils/apiClient')
      const response = await apiFetch('/api/v1/auth/password-reset/request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email })
      }, false)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(errorData.detail || 'Failed to request password reset')
      }

      const data = await response.json()
      setSuccess(data.message || 'If the email exists, a password reset link has been sent.')
      setEmail('')
    } catch (err: any) {
      setError(err.message || 'Failed to request password reset. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long')
      return
    }

    setLoading(true)

    try {
      const { apiFetch } = await import('../utils/apiClient')
      const response = await apiFetch('/api/v1/auth/password-reset/confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          token: token || '',
          new_password: newPassword
        })
      }, false)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Reset failed' }))
        throw new Error(errorData.detail || 'Failed to reset password')
      }

      const data = await response.json()
      setSuccess(data.message || 'Password has been reset successfully. You can now login.')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      setError(err.message || 'Failed to reset password. The token may be invalid or expired.')
    } finally {
      setLoading(false)
    }
  }

  // Show confirm form if token is present
  if (token) {
    return (
      <div className="password-reset-page">
        <div className="password-reset-container">
          <div className="password-reset-header">
            <h1>🛡️ SimpleSecCheck</h1>
            <p>Reset your password</p>
          </div>

          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          {success && (
            <div className="success-message" role="alert">
              {success}
              <div style={{ marginTop: '12px' }}>
                <Link to="/login" className="login-link">
                  Go to Login
                </Link>
              </div>
            </div>
          )}

          {!success && (
            <form onSubmit={handleConfirmReset} className="password-reset-form">
              <div className="form-group">
                <label htmlFor="newPassword">New Password</label>
                <input
                  id="newPassword"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  placeholder="••••••••"
                />
              </div>

              <div className="form-group">
                <label htmlFor="confirmPassword">Confirm Password</label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  placeholder="••••••••"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !newPassword || !confirmPassword}
                className="reset-button"
              >
                {loading ? 'Resetting...' : 'Reset Password'}
              </button>

              <div style={{ marginTop: '16px', textAlign: 'center' }}>
                <Link to="/login" className="back-link">
                  Back to Login
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    )
  }

  // Show request form if no token
  return (
    <div className="password-reset-page">
      <div className="password-reset-container">
        <div className="password-reset-header">
          <h1>🛡️ SimpleSecCheck</h1>
          <p>Reset your password</p>
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

        {!success && (
          <form onSubmit={handleRequestReset} className="password-reset-form">
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

            <button
              type="submit"
              disabled={loading || !email}
              className="reset-button"
            >
              {loading ? 'Sending...' : 'Send Reset Link'}
            </button>

            <div style={{ marginTop: '16px', textAlign: 'center' }}>
              <Link to="/login" className="back-link">
                Back to Login
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
