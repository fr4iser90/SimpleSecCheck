import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'

interface FeatureFlags {
  ALLOW_LOCAL_PATHS: boolean
  ALLOW_WEBSITE_SCANS: boolean
  ALLOW_API_ENDPOINT_SCANS: boolean
  ALLOW_NETWORK_HOST_SCANS: boolean
  ALLOW_KUBERNETES_CLUSTER_SCANS: boolean
  ALLOW_REMOTE_CONTAINERS: boolean
  ALLOW_LOCAL_CONTAINERS: boolean
  ALLOW_GIT_REPOS: boolean
  ALLOW_ZIP_UPLOAD: boolean
}

const FEATURE_FLAG_ORDER: (keyof FeatureFlags)[] = [
  'ALLOW_LOCAL_PATHS',
  'ALLOW_WEBSITE_SCANS',
  'ALLOW_API_ENDPOINT_SCANS',
  'ALLOW_NETWORK_HOST_SCANS',
  'ALLOW_KUBERNETES_CLUSTER_SCANS',
  'ALLOW_REMOTE_CONTAINERS',
  'ALLOW_LOCAL_CONTAINERS',
  'ALLOW_GIT_REPOS',
  'ALLOW_ZIP_UPLOAD'
]

export default function FeatureFlagsPage() {
  const [flags, setFlags] = useState<FeatureFlags>({
    ALLOW_LOCAL_PATHS: true,
    ALLOW_WEBSITE_SCANS: true,
    ALLOW_API_ENDPOINT_SCANS: true,
    ALLOW_NETWORK_HOST_SCANS: true,
    ALLOW_KUBERNETES_CLUSTER_SCANS: true,
    ALLOW_REMOTE_CONTAINERS: true,
    ALLOW_LOCAL_CONTAINERS: true,
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
        setFlags((prev) => ({ ...prev, ...data }))
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

  /** Set policy: allow all target types (all flags on). */
  const allowAllTargets = () => {
    setFlags(
      FEATURE_FLAG_ORDER.reduce((acc, key) => ({ ...acc, [key]: true }), {} as FeatureFlags)
    )
  }

  /** Set policy: only safe targets (Git repos + ZIP upload). */
  const safeTargetsOnly = () => {
    setFlags({
      ALLOW_LOCAL_PATHS: false,
      ALLOW_WEBSITE_SCANS: false,
      ALLOW_API_ENDPOINT_SCANS: false,
      ALLOW_NETWORK_HOST_SCANS: false,
      ALLOW_KUBERNETES_CLUSTER_SCANS: false,
      ALLOW_REMOTE_CONTAINERS: false,
      ALLOW_LOCAL_CONTAINERS: false,
      ALLOW_GIT_REPOS: true,
      ALLOW_ZIP_UPLOAD: true
    })
  }

  const flagDescriptions: Record<keyof FeatureFlags, { name: string, description: string; targets?: string; useCaseDefault?: string }> = {
    ALLOW_LOCAL_PATHS: {
      name: 'Local Paths',
      description: 'Allow local filesystem paths as scan targets. When enabled, only administrators can use local path scanning (dangerous target).',
      targets: 'Targets: host paths (e.g. /path/to/project).',
      useCaseDefault: 'Default on: Solo. Off: Network Intern, Public Web, Enterprise. Admin-only when on.'
    },
    ALLOW_WEBSITE_SCANS: {
      name: 'Website scans',
      description: 'Allow scanning website URLs (https://…).',
      targets: 'Targets: website URLs.',
      useCaseDefault: 'Default on: Solo, Network Intern, Enterprise. Off: Public Web.'
    },
    ALLOW_API_ENDPOINT_SCANS: {
      name: 'API endpoint scans',
      description: 'Allow scanning API endpoints (REST/GraphQL).',
      targets: 'Targets: API endpoint URLs.',
      useCaseDefault: 'Default on: Solo, Network Intern, Enterprise. Off: Public Web.'
    },
    ALLOW_NETWORK_HOST_SCANS: {
      name: 'Network host scans',
      description: 'Allow scanning network hosts (IP/hostname, port checks).',
      targets: 'Targets: IP addresses, hostnames.',
      useCaseDefault: 'Default on: Solo, Network Intern, Enterprise. Off: Public Web. Admin-only when on.'
    },
    ALLOW_KUBERNETES_CLUSTER_SCANS: {
      name: 'Kubernetes cluster scans',
      description: 'Allow scanning live Kubernetes clusters.',
      targets: 'Targets: Kubernetes API.',
      useCaseDefault: 'Default on: Solo, Network Intern, Enterprise. Off: Public Web.'
    },
    ALLOW_REMOTE_CONTAINERS: {
      name: 'Container Registry (external images)',
      description: 'Allow scanning images from external registries only (not local Docker).',
      targets: 'Targets: Docker Hub, ghcr.io, gcr.io, ECR, etc. — i.e. remote image references only.',
      useCaseDefault: 'Default on: Solo, Network Intern, Enterprise. Off: Public Web.'
    },
    ALLOW_LOCAL_CONTAINERS: {
      name: 'Local Containers (dangerous, admin only)',
      description: 'Allow scanning images from local Docker or local registry. When enabled, only administrators can use this.',
      targets: 'Targets: localhost, 127.0.0.1, local/… (local registry or Docker daemon).',
      useCaseDefault: 'Default on: Solo, Network Intern, Enterprise. Off: Public Web. Admin-only when on.'
    },
    ALLOW_GIT_REPOS: {
      name: 'Git Repositories',
      description: 'Allow Git repository scans (GitHub, GitLab, etc.).',
      targets: 'Targets: GitHub, GitLab repo URLs.',
      useCaseDefault: 'Default on: all use cases.'
    },
    ALLOW_ZIP_UPLOAD: {
      name: 'ZIP Upload',
      description: 'Allow ZIP file uploads as scan targets. Safe for all deployment types.',
      targets: 'Targets: uploaded ZIP archives.',
      useCaseDefault: 'Default on: all use cases.'
    }
  }

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1>Feature Flags</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
          Allowed targets depend on this policy. Toggle individual target types or use a preset below.
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
          background: 'var(--glass-bg-main)',
          padding: '2rem',
          borderRadius: '8px',
          border: '1px solid var(--glass-border-main)'
        }}>
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.75rem',
            marginBottom: '1.5rem',
            paddingBottom: '1.5rem',
            borderBottom: '1px solid var(--glass-border-main)'
          }}>
            <span style={{ color: 'var(--text-secondary)', alignSelf: 'center', marginRight: '0.5rem' }}>Policy presets:</span>
            <button
              type="button"
              onClick={allowAllTargets}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: '1px solid var(--glass-border-main)',
                background: 'rgba(255, 255, 255, 0.05)',
                color: 'var(--text-main)',
                cursor: 'pointer'
              }}
            >
              Allow all targets
            </button>
            <button
              type="button"
              onClick={safeTargetsOnly}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: '1px solid var(--glass-border-main)',
                background: 'rgba(255, 255, 255, 0.05)',
                color: 'var(--text-main)',
                cursor: 'pointer'
              }}
            >
              Safe targets only (Git + ZIP)
            </button>
          </div>
          {FEATURE_FLAG_ORDER.map((key) => (
            <div
              key={key}
              style={{
                padding: '1.5rem',
                marginBottom: '1rem',
                background: 'rgba(255, 255, 255, 0.02)',
                borderRadius: '8px',
                border: '1px solid var(--glass-border-main)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div style={{ flex: 1 }}>
                <h3 style={{ margin: 0, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {(key === 'ALLOW_LOCAL_PATHS' || key === 'ALLOW_LOCAL_CONTAINERS') && (
                    <span title="Admin only when enabled">⚠️</span>
                  )}
                  {flagDescriptions[key].name}
                </h3>
                <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                  {flagDescriptions[key].description}
                </p>
                {flagDescriptions[key].targets && (
                  <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)', opacity: 0.9 }}>
                    {flagDescriptions[key].targets}
                  </p>
                )}
                {flagDescriptions[key].useCaseDefault && (
                  <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.75rem', color: 'var(--color-info, #0dcaf0)' }}>
                    {flagDescriptions[key].useCaseDefault}
                  </p>
                )}
                {key === 'ALLOW_LOCAL_PATHS' && flags.ALLOW_LOCAL_PATHS && (
                  <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.8rem', color: 'var(--color-info, #0dcaf0)' }}>
                    Only admins can start scans with local paths. Other users will get a permission error.
                  </p>
                )}
                {key === 'ALLOW_LOCAL_CONTAINERS' && flags.ALLOW_LOCAL_CONTAINERS && (
                  <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.8rem', color: 'var(--color-info, #0dcaf0)' }}>
                    Only admins can scan local images (localhost, 127.0.0.1, local/…). Remote registry (Docker Hub, etc.) is controlled by the toggle above.
                  </p>
                )}
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
