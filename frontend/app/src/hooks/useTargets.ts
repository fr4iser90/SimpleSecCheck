import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'

export interface AutoScanConfig {
  enabled: boolean
  mode: 'interval' | 'event'
  interval_seconds?: number | null
  event?: 'push' | 'webhook' | null
}

export interface LastScanSummary {
  scan_id: string
  status: string
  completed_at: string | null
  total_vulnerabilities: number
  critical_vulnerabilities: number
  high_vulnerabilities: number
  medium_vulnerabilities: number
  low_vulnerabilities: number
}

export interface ScanTargetItem {
  id: string
  user_id: string
  type: string
  source: string
  display_name: string | null
  auto_scan: AutoScanConfig
  config: Record<string, unknown>
  created_at: string
  updated_at: string
  scanners?: string[]
  last_scan?: LastScanSummary | null
}

export function useTargets(targetType?: string | null) {
  const [targets, setTargets] = useState<ScanTargetItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadTargets = async () => {
    setLoading(true)
    setError(null)
    try {
      const q = targetType ? `?target_type=${encodeURIComponent(targetType)}` : ''
      const response = await apiFetch(`/api/user/targets${q}`)
      if (response.ok) {
        const data = await response.json()
        setTargets(Array.isArray(data) ? data : [])
      } else {
        setError('Failed to load targets')
      }
    } catch (err) {
      console.error('Failed to load targets:', err)
      setError('Failed to load targets')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTargets()
  }, [targetType ?? ''])

  const triggerScan = async (targetId: string): Promise<{ success: boolean; scan_id?: string; error?: string }> => {
    try {
      const response = await apiFetch(`/api/user/targets/${targetId}/scan`, {
        method: 'POST',
      })
      if (response.ok) {
        const data = await response.json()
        return { success: true, scan_id: data.scan_id }
      }
      const err = await response.json().catch(() => ({}))
      return { success: false, error: err.detail || 'Failed to start scan' }
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : 'Failed to start scan' }
    }
  }

  return { targets, loading, error, loadTargets, triggerScan }
}
