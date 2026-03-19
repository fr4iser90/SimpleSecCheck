import { useState, useEffect, ReactNode } from 'react'
import { resolveApiUrl } from '../utils/resolveApiUrl'

export interface SetupStatus {
  setup_required: boolean
  setup_complete: boolean
  database_connected: boolean
  tables_exist: Record<string, boolean>
  admin_exists: boolean
  system_state_exists: boolean
}

interface BootstrapLoaderProps {
  children: (setupStatus: SetupStatus) => ReactNode
}

/**
 * BootstrapLoader component that checks setup status before rendering routes.
 * This ensures setup status is known before any routing decisions are made.
 */
export default function BootstrapLoader({ children }: BootstrapLoaderProps) {
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    checkSetupStatus()
  }, [])

  const checkSetupStatus = async () => {
    try {
      setLoading(true)
      setError(null)

      // Retry logic: Backend might be starting up (Docker Compose)
      const maxRetries = 3
      const retryDelays = [1000, 2000, 4000] // Exponential backoff: 1s, 2s, 4s

      for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
          // Create timeout controller for older browsers
          const controller = new AbortController()
          const timeoutId = setTimeout(() => controller.abort(), 5000) // 5s timeout per request

          const response = await fetch(resolveApiUrl('/api/setup/status'), {
            signal: controller.signal
          })

          clearTimeout(timeoutId)

          // Backend responded - parse response
          if (response.ok) {
            const data = await response.json()
            setSetupStatus(data)
            setLoading(false)
            return
          }

          // Backend responded with error (4xx/5xx)
          // This means backend is running but setup is not complete
          // No need to retry - backend is up, just not configured
          setSetupStatus({
            setup_required: true,
            setup_complete: false,
            database_connected: false,
            tables_exist: {},
            admin_exists: false,
            system_state_exists: false
          })
          setLoading(false)
          return
        } catch (err: any) {
          // Network error or timeout - backend might be starting
          const isLastAttempt = attempt === maxRetries - 1
          const isNetworkError = err.name === 'TypeError' || err.name === 'AbortError'

          if (isLastAttempt) {
            // Final attempt failed - assume setup required
            // This handles: backend not started, network issues, etc.
            console.warn('Setup status check failed after retries:', err)
            setSetupStatus({
              setup_required: true,
              setup_complete: false,
              database_connected: false,
              tables_exist: {},
              admin_exists: false,
              system_state_exists: false
            })
            setLoading(false)
            return
          }

          // Wait before retry (only for network errors)
          if (isNetworkError) {
            await new Promise(resolve => setTimeout(resolve, retryDelays[attempt]))
          } else {
            // Non-network error - don't retry
            setSetupStatus({
              setup_required: true,
              setup_complete: false,
              database_connected: false,
              tables_exist: {},
              admin_exists: false,
              system_state_exists: false
            })
            setLoading(false)
            return
          }
        }
      }
    } catch (err: any) {
      // Fallback error handling
      console.error('Setup status check failed:', err)
      setError('Failed to check setup status. Please ensure the backend is running.')
      setSetupStatus({
        setup_required: true,
        setup_complete: false,
        database_connected: false,
        tables_exist: {},
        admin_exists: false,
        system_state_exists: false
      })
      setLoading(false)
    }
  }

  // Show loading screen while checking setup status
  if (loading || !setupStatus) {
    return (
      <div className="app">
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          flexDirection: 'column',
          gap: '20px'
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '4px solid #f3f3f3',
            borderTop: '4px solid #007bff',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto'
          }}></div>
          <p style={{ color: '#666', fontSize: '16px' }}>Checking system setup...</p>
        </div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    )
  }

  // Show error screen if setup check failed (should not happen due to fallback)
  if (error && !setupStatus) {
    return (
      <div className="app">
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          flexDirection: 'column',
          gap: '20px',
          padding: '20px'
        }}>
          <div style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            background: '#dc3545',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            color: 'white',
            fontSize: '24px',
            fontWeight: 'bold'
          }}>!</div>
          <h2 style={{ color: '#333', textAlign: 'center' }}>Setup Error</h2>
          <p style={{ color: '#666', textAlign: 'center', maxWidth: '600px' }}>
            {error}
          </p>
          <button
            onClick={checkSetupStatus}
            style={{
              padding: '12px 24px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '16px',
              cursor: 'pointer'
            }}
          >
            Retry Setup Check
          </button>
        </div>
      </div>
    )
  }

  // Render children with setup status
  return <>{children(setupStatus)}</>
}
