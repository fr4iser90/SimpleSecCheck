import { useState, useEffect } from 'react'
import { resolveApiUrl } from '../utils/resolveApiUrl'

interface RateLimitInfo {
  remaining: number
  used: number
  limit: number
  reset_timestamp: number | null
  reset_time: string | null
  has_token: boolean
  estimated_requests_available: number
}

export default function RateLimitIndicator() {
  const [rateLimit, setRateLimit] = useState<RateLimitInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRateLimit = async () => {
      try {
        const response = await fetch(resolveApiUrl('/api/github/rate-limit'))
        if (!response.ok) {
          throw new Error('Failed to fetch rate limit')
        }
        const data = await response.json()
        setRateLimit(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchRateLimit()
    // Refresh every 30 seconds
    const interval = setInterval(fetchRateLimit, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div style={{ fontSize: '0.875rem', color: '#6c757d' }}>
        🔄 Loading rate limit info...
      </div>
    )
  }

  if (error || !rateLimit) {
    return null // Don't show error, just hide the indicator
  }

  const percentage = (rateLimit.remaining / rateLimit.limit) * 100
  const isLow = percentage < 20
  const isVeryLow = percentage < 10

  const getColor = () => {
    if (isVeryLow) return '#dc3545'
    if (isLow) return '#ffc107'
    return '#28a745'
  }

  const getResetTime = () => {
    if (!rateLimit.reset_timestamp) return null
    const resetDate = new Date(rateLimit.reset_timestamp * 1000)
    const now = new Date()
    const diffMs = resetDate.getTime() - now.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return 'soon'
    if (diffMins < 60) return `in ${diffMins} min`
    const diffHours = Math.floor(diffMins / 60)
    return `in ${diffHours} h`
  }

  return (
    <div style={{
      padding: '0.75rem',
      background: isLow ? 'rgba(255, 193, 7, 0.1)' : 'rgba(40, 167, 69, 0.1)',
      border: `1px solid ${getColor()}`,
      borderRadius: '6px',
      fontSize: '0.875rem',
      marginBottom: '1rem'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontWeight: 'bold' }}>GitHub API Rate Limit</span>
          {rateLimit.has_token ? (
            <span style={{ fontSize: '0.75rem', color: '#28a745' }}>✓ Token</span>
          ) : (
            <span style={{ fontSize: '0.75rem', color: '#ffc107' }}>⚠ No Token</span>
          )}
        </div>
        <span style={{ color: getColor(), fontWeight: 'bold' }}>
          {rateLimit.remaining} / {rateLimit.limit}
        </span>
      </div>
      
      <div style={{
        width: '100%',
        height: '8px',
        background: '#e9ecef',
        borderRadius: '4px',
        overflow: 'hidden',
        marginBottom: '0.5rem'
      }}>
        <div style={{
          width: `${percentage}%`,
          height: '100%',
          background: getColor(),
          transition: 'width 0.3s ease'
        }} />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#6c757d' }}>
        <span>
          {rateLimit.used} requests used
        </span>
        {rateLimit.reset_timestamp && (
          <span>
            Resets {getResetTime()}
          </span>
        )}
      </div>

      {isLow && (
        <div style={{
          marginTop: '0.5rem',
          padding: '0.5rem',
          background: 'rgba(220, 53, 69, 0.1)',
          borderRadius: '4px',
          fontSize: '0.75rem',
          color: '#dc3545'
        }}>
          {isVeryLow ? '⚠️ Very low rate limit! Consider adding a GitHub token.' : '⚠️ Rate limit is low. Consider adding a GitHub token for higher limits.'}
        </div>
      )}

      {!rateLimit.has_token && (
        <div style={{
          marginTop: '0.5rem',
          padding: '0.5rem',
          background: 'rgba(255, 193, 7, 0.1)',
          borderRadius: '4px',
          fontSize: '0.75rem',
          color: '#856404'
        }}>
          💡 Tip: Add GITHUB_TOKEN to .env for 5000 requests/hour (vs 60 without token)
        </div>
      )}
    </div>
  )
}
