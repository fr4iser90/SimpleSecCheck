import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { apiFetch } from '../utils/apiClient'

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState<string>('')

  useEffect(() => {
    if (!token || token.length < 10) {
      setStatus('error')
      setMessage('Invalid or missing verification link.')
      return
    }
    const verify = async () => {
      try {
        const response = await apiFetch(
          `/api/v1/auth/verify-email?token=${encodeURIComponent(token)}&redirect=false`,
          {},
          false
        )
        const data = await response.json().catch(() => ({}))
        if (response.ok && data.verified) {
          setStatus('success')
          setMessage(data.message || 'Email verified successfully.')
        } else {
          setStatus('error')
          setMessage(data.detail || 'Verification failed. The link may be invalid or expired.')
        }
      } catch {
        setStatus('error')
        setMessage('Verification failed. Please try again or request a new link.')
      }
    }
    verify()
  }, [token])

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>🛡️ SimpleSecCheck</h1>
          <p>Email verification</p>
        </div>
        {status === 'loading' && (
          <p style={{ textAlign: 'center', marginTop: '1rem' }}>Verifying your email...</p>
        )}
        {status === 'success' && (
          <>
            <div className="success-message" role="alert">
              {message}
            </div>
            <div style={{ marginTop: '1rem', textAlign: 'center' }}>
              <Link to="/login" className="primary" style={{ display: 'inline-block', padding: '0.5rem 1rem' }}>
                Sign in
              </Link>
            </div>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="error-message" role="alert">
              {message}
            </div>
            <div style={{ marginTop: '1rem', textAlign: 'center' }}>
              <Link to="/login" style={{ color: 'var(--color-primary)', textDecoration: 'none', fontSize: '14px' }}>
                ← Back to Sign in
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
