import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useConfig } from '../hooks/useConfig'
import MainLayout from './MainLayout'

function AuthRouteLoading() {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        flexDirection: 'column',
        gap: '20px',
      }}
    >
      <div
        style={{
          width: '40px',
          height: '40px',
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #007bff',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }}
      />
      <p style={{ color: '#666', fontSize: '16px' }}>Loading...</p>
    </div>
  )
}

/**
 * Instance login policy: when login is required, unauthenticated users are sent to /login.
 * In free / open mode, guests may use the app without signing in.
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const { config } = useConfig()

  if (authLoading) {
    return <AuthRouteLoading />
  }

  if (!config || config.auth_mode === 'free' || !config.login_required) {
    return <>{children}</>
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

/**
 * Admin UI: always requires an authenticated user with role `admin`.
 * Mirrors backend `get_admin_user` so the router UX matches API 401/403.
 */
export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading: authLoading, user } = useAuth()
  const { config } = useConfig()

  if (authLoading) {
    return <AuthRouteLoading />
  }

  const loginRequired =
    Boolean(config && config.auth_mode !== 'free' && config.login_required)

  if (!isAuthenticated) {
    if (loginRequired) {
      return <Navigate to="/login" replace />
    }
    return (
      <MainLayout>
        <div className="admin-dashboard-page">
          <div className="admin-dashboard-container">
            <h2>Access denied</h2>
            <p>Sign in as an administrator to use this area.</p>
            <p>
              <Link to="/login">Sign in</Link>
              {' · '}
              <Link to="/">Home</Link>
            </p>
          </div>
        </div>
      </MainLayout>
    )
  }

  if (user?.role !== 'admin') {
    return (
      <MainLayout>
        <div className="admin-dashboard-page">
          <div className="admin-dashboard-container">
            <h2>Access denied</h2>
            <p>Administrator privileges are required.</p>
            <p>
              <Link to="/">Back to home</Link>
            </p>
          </div>
        </div>
      </MainLayout>
    )
  }

  return <>{children}</>
}
