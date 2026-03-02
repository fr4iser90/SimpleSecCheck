import { useState, useEffect } from 'react'

export interface FrontendConfig {
  environment: string
  is_production: boolean
  features: {
    scan_types: {
      code: boolean
      website: boolean
      network: boolean
    }
    bulk_scan: boolean
    local_paths: boolean
    git_only: boolean
    queue_enabled: boolean
    session_management: boolean
    metadata_collection: 'always' | 'optional'
    auto_shutdown: boolean
    zip_upload: boolean
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
        const response = await fetch('/api/config')
        if (!response.ok) {
          throw new Error('Failed to fetch config')
        }
        const data = await response.json()
        setConfig(data)
        setError(null)
      } catch (err) {
        console.error('Failed to load frontend config:', err)
        setError(err instanceof Error ? err.message : 'Unknown error')
        // Fallback to dev mode if config fails
        setConfig({
          environment: 'dev',
          is_production: false,
          features: {
            scan_types: { code: true, website: true, network: true },
            bulk_scan: true,
            local_paths: true,
            git_only: false,
            queue_enabled: false,
            session_management: false,
            metadata_collection: 'optional',
            auto_shutdown: true,
            zip_upload: true,
          },
          queue: null,
          rate_limits: null,
        })
      } finally {
        setLoading(false)
      }
    }

    fetchConfig()
  }, [])

  return { config, loading, error }
}
