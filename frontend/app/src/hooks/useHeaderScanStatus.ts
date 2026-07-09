import { useEffect, useRef, useState } from 'react'
import { SSE_ENVELOPE_EVENT, type SseEnvelope } from '../hooks/useGlobalSse'
import type { ScanRunStatus, ScanStatusState } from '../types/scanStatus'

export function useHeaderScanStatus(): ScanStatusState {
  const [scanStatus, setScanStatus] = useState<ScanStatusState>({
    status: 'idle',
    scan_id: null,
    results_dir: null,
    started_at: null,
  })
  const statusKeyRef = useRef('')

  useEffect(() => {
    let cancelled = false

    const applyStatus = (next: ScanStatusState) => {
      const k = JSON.stringify({
        status: next.status,
        scan_id: next.scan_id,
        started_at: next.started_at,
        results_dir: next.results_dir,
      })
      if (k === statusKeyRef.current) return
      statusKeyRef.current = k
      setScanStatus(next)
    }

    const tick = async () => {
      try {
        const { apiFetch } = await import('../utils/apiClient')
        const running = await apiFetch(
          '/api/v1/scans/?status=running&limit=1&sort_by=created_at&sort_order=desc',
        )
        if (!running.ok || cancelled) return
        const runs = await running.json()
        let scanId: string | null = null
        if (Array.isArray(runs) && runs.length > 0) {
          scanId = runs[0].id
        }
        if (!scanId) {
          const pend = await apiFetch(
            '/api/v1/scans/?status=pending&limit=1&sort_by=created_at&sort_order=desc',
          )
          if (!pend.ok || cancelled) return
          const ps = await pend.json()
          if (Array.isArray(ps) && ps.length > 0) {
            applyStatus({
              status: 'pending',
              scan_id: ps[0].id,
              results_dir: null,
              started_at: ps[0].started_at || null,
            })
            return
          }
        }
        if (!scanId) {
          applyStatus({
            status: 'idle',
            scan_id: null,
            results_dir: null,
            started_at: null,
          })
          return
        }
        const sr = await apiFetch(`/api/v1/scans/${encodeURIComponent(scanId)}/status`)
        if (!sr.ok || cancelled) return
        const d = await sr.json()
        applyStatus({
          status: d.status as ScanRunStatus,
          scan_id: d.scan_id,
          results_dir: d.scan_id,
          started_at: d.started_at ?? null,
        })
      } catch (e) {
        console.error('Scan status refresh:', e)
      }
    }

    void tick()

    const onEnv = (e: Event) => {
      const env = (e as CustomEvent<SseEnvelope>).detail
      if (!env || env.v !== 1) return
      if (env.type === 'scan_update' || env.type === 'queue_update') void tick()
    }
    window.addEventListener(SSE_ENVELOPE_EVENT, onEnv)
    return () => {
      cancelled = true
      window.removeEventListener(SSE_ENVELOPE_EVENT, onEnv)
    }
  }, [])

  return scanStatus
}
