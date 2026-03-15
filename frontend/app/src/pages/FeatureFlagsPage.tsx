import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'

interface FeatureFlags {
  ALLOW_LOCAL_PATHS: boolean
  ALLOW_NETWORK_SCANS: boolean
  ALLOW_CONTAINER_REGISTRY: boolean
  ALLOW_GIT_REPOS: boolean
  ALLOW_ZIP_UPLOAD: boolean
}

export default function FeatureFlagsPage() {
  const [flags, setFlags] = useState<FeatureFlags>({
    ALLOW_LOCAL_PATHS: true,
    ALLOW_NETWORK_SCANS: true,
    ALLOW_CONTAINER_REGISTRY: true,
    ALLOW_GIT_REPOS: true,
    ALLOW_ZIP_UPLOAD: true
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const loadFlags = async () => {
    setLoading(true)
    try {
      const response = await apiFetch('/api/admin/feature-flags')
      if (response.ok) {
        const data = await response.json()
        setFlags(data)
      }
    } catch (error) {
      console.error('Failed to load feature flags:', error)
      setMessage({ type: 'error', text: 'Failed to load feature flags' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadFlags()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const response = await apiFetch('/api/admin/feature-flags', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(flags)
      })
      if (response.ok) {
        setMessage({ type: 'success', text: 'Feature flags updated successfully' })
        setTimeout(() => setMessage(null), 3000)
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to update feature flags' })
      }
    } catch (error) {
      console.error('Failed to save feature flags:', error)
      setMessage({ type: 'error', text: 'Failed to save feature flags' })
    } finally {
      setSaving(false)
    }
  }

  const toggleFlag = (key: keyof FeatureFlags) => {
    setFlags({ ...flags, [key]: !flags[key] })
  }

  const flagDescriptions: Record<keyof FeatureFlags, { name: string, description: string }> = {
    ALLOW_LOCAL_PATHS: {
      name: 'Local Paths',
      description: 'Allow local filesystem paths as scan targets. Only safe for single-user deployments.'
    },
    ALLOW_NETWORK_SCANS: {
      name: 'Network Scans',
      description: 'Allow network/website scans and external target scanning.'
    },
    ALLOW_CONTAINER_REGISTRY: {
      name: 'Container Registry',
      description: 'Allow container registry scans (Docker, OCI images).'
    },
    ALLOW_GIT_REPOS: {
      name: 'Git Repositories',
      description: 'Allow Git repository scans (GitHub, GitLab, etc.).'
    },
    ALLOW_ZIP_UPLOAD: {
      name: 'ZIP Upload',
      description: 'Allow ZIP file uploads as scan targets. Safe for all deployment types.'
    }
  }

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1>Feature Flags</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
          Granular control over which target types are allowed in the system
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
      ) : (
        <div style={{
          background: 'var(--glass-bg-dark)',
          padding: '2rem',
          borderRadius: '8px',
          border: '1px solid var(--glass-border-dark)'
        }}>
          {(Object.keys(flags) as Array<keyof FeatureFlags>).map((key) => (
            <div
              key={key}
              style={{
                padding: '1.5rem',
                marginBottom: '1rem',
                background: 'rgba(255, 255, 255, 0.02)',
                borderRadius: '8px',
                border: '1px solid var(--glass-border-dark)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div style={{ flex: 1 }}>
                <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>
                  {flagDescriptions[key].name}
                </h3>
                <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                  {flagDescriptions[key].description}
                </p>
              </div>
              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                cursor: 'pointer'
              }}>
                <input
                  type="checkbox"
                  checked={flags[key]}
                  onChange={() => toggleFlag(key)}
                  style={{
                    width: '2rem',
                    height: '2rem',
                    cursor: 'pointer'
                  }}
                />
                <span style={{
                  color: flags[key] ? 'var(--color-pass)' : 'var(--text-secondary)',
                  fontWeight: flags[key] ? 600 : 400
                }}>
                  {flags[key] ? 'Enabled' : 'Disabled'}
                </span>
              </label>
            </div>
          ))}

          <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              className="primary"
              onClick={handleSave}
              disabled={saving}
              style={{ minWidth: '150px' }}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
