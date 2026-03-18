import { useState, useEffect } from 'react'

export interface FrontendConfig {
  auth_mode: 'free' | 'basic' | 'jwt'
  access_mode: 'public' | 'mixed' | 'private'
  login_required: boolean
  features: {
    bulk_scan: boolean
    bulk_scan_allow_guests?: boolean
    session_management: boolean
    metadata_collection: 'always' | 'optional'
    zip_upload: boolean
    scanner_assets_auto_update_enabled: boolean
  }
  scan_types: {
    [key: string]: {
      enabled: boolean
      label: string
      backend_value: string
      description?: string
    }
  }
  allowed_targets: {
    local_paths: boolean
    git_repos: boolean
    zip_upload: boolean
    container_registry: boolean
    local_containers: boolean
    website?: boolean
    api_endpoint?: boolean
    network_host?: boolean
    kubernetes_cluster?: boolean
    network: boolean
  }
  /** Human-readable labels for allowed targets (from backend; for "Allowed targets: …" help text) */
  allowed_targets_display?: string[]
  permissions: {
    dangerous_targets: string[]
    target_security_level: Record<string, string>
    target_permission_map: Record<string, string>
  }
  queue: {
    strategy: string
    max_length: number
    public_view: boolean
  } | null
  rate_limits: {
    scans_per_session: number
    requests_per_session: number
  } | null
}

export function useConfig() {
  const [config, setConfig] = useState<FrontendConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const { apiFetch } = await import('../utils/apiClient')
        const response = await apiFetch('/api/config', {}, false)
        if (!response.ok) {
          throw new Error('Failed to fetch config')
        }
        const data = await response.json()
        setConfig(data)
        setError(null)
      } catch (err) {
        console.error('Failed to load frontend config:', err)
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchConfig()
  }, [])

  return { config, loading, error }
}
