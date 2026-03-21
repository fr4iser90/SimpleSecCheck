import { useState, useEffect, useRef, useCallback } from 'react'
import { apiFetch } from '../utils/apiClient'
import { useAuth } from './useAuth'
import { SSE_ENVELOPE_EVENT, type SseEnvelope } from './useGlobalSse'

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

export interface ActiveScanSummary {
  scan_id: string
  status: string
  queue_position: number | null
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
  /** ISO datetime when next interval scan is due (null if not auto-interval or no last scan). */
  next_scan_at?: string | null
  initial_scan_paused?: boolean
  /** ISO datetime when initial scan was enqueued (null if not yet). */
  initial_scan_triggered_at?: string | null
  /** Pending or running scan for this target (from API). */
  active_scan?: ActiveScanSummary | null
}

/** Response shape for `GET /api/user/targets` (no legacy array). */
export interface ScanTargetsListResponse {
  revision: string
  targets: ScanTargetItem[]
}

function etagIfNoneMatch(revision: string): string {
  if (!revision) return ''
  if (revision.startsWith('W/')) return revision
  return `W/"${revision}"`
}

function revisionFromResponse(response: Response, body: { revision?: string }): string {
  const et = response.headers.get('ETag')?.trim()
  if (et?.startsWith('W/"') && et.endsWith('"')) return et.slice(3, -1)
  if (body.revision && typeof body.revision === 'string') return body.revision
  return ''
}

export function isScanTargetsListResponse(data: unknown): data is ScanTargetsListResponse {
  if (!data || typeof data !== 'object') return false
  const o = data as Record<string, unknown>
  return typeof o.revision === 'string' && Array.isArray(o.targets)
}

export function useTargets(targetType?: string | null) {
  const { isAuthenticated } = useAuth()
  const [targets, setTargets] = useState<ScanTargetItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const revisionRef = useRef<string>('')

  const loadTargets = useCallback(
    async (options?: { silent?: boolean }) => {
      const silent = options?.silent === true
      if (!silent) {
        setLoading(true)
        setError(null)
      }
      try {
        const q = targetType ? `?target_type=${encodeURIComponent(targetType)}` : ''
        const headers: Record<string, string> = {}
        const inm = etagIfNoneMatch(revisionRef.current)
        if (inm) headers['If-None-Match'] = inm
        const response = await apiFetch(`/api/user/targets${q}`, { headers })
        if (response.status === 304) {
          if (!silent) setLoading(false)
          return
        }
        if (response.ok) {
          const data: unknown = await response.json()
          if (!isScanTargetsListResponse(data)) {
            if (!silent) setError('Failed to load targets')
            return
          }
          const rev = revisionFromResponse(response, data)
          if (rev) revisionRef.current = rev
          setTargets(data.targets)
        } else if (!silent) {
          setError('Failed to load targets')
        }
      } catch (err) {
        console.error('Failed to load targets:', err)
        if (!silent) setError('Failed to load targets')
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [targetType]
  )

  useEffect(() => {
    revisionRef.current = ''
    void loadTargets({ silent: false })
  }, [loadTargets])

  useEffect(() => {
    const onEnv = (e: Event) => {
      const env = (e as CustomEvent<SseEnvelope>).detail
      if (!env || env.v !== 1) return

      if (env.type === 'scan_update') {
        const p = env.payload as { list_revision?: string }
        const incoming = typeof p.list_revision === 'string' ? p.list_revision : ''
        if (incoming && incoming === revisionRef.current) {
          return
        }
        void loadTargets({ silent: true })
        return
      }

      if (env.type !== 'target_update' || env.scope !== 'targets') return
      const p = env.payload as {
        action?: string
        list_revision?: string
        target?: ScanTargetItem
        target_id?: string
      }
      const rev = typeof p.list_revision === 'string' ? p.list_revision : ''
      if (rev) revisionRef.current = rev

      if (p.action === 'refetch') {
        void loadTargets({ silent: true })
        return
      }

      if (p.action === 'remove' && p.target_id) {
        setTargets((prev) => prev.filter((t) => t.id !== p.target_id))
        return
      }

      if (p.action === 'upsert' && p.target) {
        if (targetType && p.target.type !== targetType) {
          void loadTargets({ silent: true })
          return
        }
        setTargets((prev) => {
          const t = p.target!
          const i = prev.findIndex((x) => x.id === t.id)
          return i >= 0 ? [...prev.slice(0, i), t, ...prev.slice(i + 1)] : [...prev, t]
        })
      }
    }
    window.addEventListener(SSE_ENVELOPE_EVENT, onEnv)
    return () => window.removeEventListener(SSE_ENVELOPE_EVENT, onEnv)
  }, [loadTargets, targetType])

  useEffect(() => {
    if (isAuthenticated) return undefined
    const t = window.setInterval(() => {
      void loadTargets({ silent: true })
    }, 45000)
    return () => clearInterval(t)
  }, [isAuthenticated, loadTargets])

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
