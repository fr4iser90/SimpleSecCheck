import { useState, useEffect } from 'react'

export interface FrontendConfig {
  environment: string
  is_production: boolean
  auth_mode: 'free' | 'basic' | 'jwt'
  /** Who may use the system: public (all open) | mixed (public scan/queue, login for dashboard) | private (login required) */
  access_mode: 'public' | 'mixed' | 'private'
  login_required: boolean
  features: {
    scan_types: {
      [key: string]: {
        enabled: boolean
        label: string
        backend_value: string
        description?: string
      }
    }
    bulk_scan: boolean
    /** If true, guests may use bulk scan (admin override). Default: only logged-in users. */
    bulk_scan_allow_guests?: boolean
    /** Queue strategy: fifo | priority | round_robin */
    queue_strategy?: string
    local_paths: boolean
    git_only: boolean
    queue_enabled: boolean
    session_management: boolean
    metadata_collection: 'always' | 'optional'
    auto_shutdown: boolean
    zip_upload: boolean
    owasp_auto_update_enabled: boolean
    /** Target types that require admin (e.g. local_mount). From API config. */
    dangerous_targets?: string[]
    target_security_level?: Record<string, string>
    target_permission_map?: Record<string, string>
    allow_local_containers?: boolean
  }
  queue: {
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
