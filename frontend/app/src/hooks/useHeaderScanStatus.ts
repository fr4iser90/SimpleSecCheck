import { useCallback, useEffect, useRef, useState } from 'react'
import { SSE_ENVELOPE_EVENT, type SseEnvelope } from '../hooks/useGlobalSse'
import type { ScanRunStatus, ScanStatusState } from '../types/scanStatus'

/** ScanView / other surfaces can nudge the header to re-query the API. */
export const SCAN_STATUS_REFRESH_EVENT = 'ssc:scan-status-refresh'

const TERMINAL: ScanRunStatus[] = ['completed', 'failed', 'cancelled', 'interrupted']

export function useHeaderScanStatus(): ScanStatusState {
  const [scanStatus, setScanStatus] = useState<ScanStatusState>({
    status: 'idle',
    scan_id: null,
    results_dir: null,
    started_at: null,
  })
  const statusKeyRef = useRef('')
  const activeRef = useRef(false)

  const applyStatus = useCallback((next: ScanStatusState) => {
    const k = JSON.stringify({
      status: next.status,
      scan_id: next.scan_id,
      started_at: next.started_at,
      results_dir: next.results_dir,
    })
    if (k === statusKeyRef.current) return
    statusKeyRef.current = k
    activeRef.current = next.status === 'pending' || next.status === 'running'
    setScanStatus(next)
  }, [])

  const tick = useCallback(async () => {
    try {
      const { apiFetch } = await import('../utils/apiClient')

      let candidateId: string | null = null

      const running = await apiFetch(
        '/api/v1/scans/?status=running&limit=1&sort_by=created_at&sort_order=desc',
      )
      if (running.ok) {
        const runs = await running.json()
        if (Array.isArray(runs) && runs.length > 0) {
          candidateId = runs[0].id
        }
      }

      if (!candidateId) {
        const pend = await apiFetch(
          '/api/v1/scans/?status=pending&limit=1&sort_by=created_at&sort_order=desc',
        )
        if (pend.ok) {
          const ps = await pend.json()
          if (Array.isArray(ps) && ps.length > 0) {
            candidateId = ps[0].id
          }
        }
      }

      if (!candidateId) {
        applyStatus({
          status: 'idle',
          scan_id: null,
          results_dir: null,
          started_at: null,
        })
        return
      }

      const sr = await apiFetch(`/api/v1/scans/${encodeURIComponent(candidateId)}/status`)
      if (!sr.ok) return
      const d = await sr.json()
      const st = String(d.status ?? '').toLowerCase() as ScanRunStatus

      // Header pill = active work only; terminal scans are not "running"
      if (TERMINAL.includes(st)) {
        applyStatus({
          status: 'idle',
          scan_id: null,
          results_dir: null,
          started_at: null,
        })
        return
      }

      applyStatus({
        status: st,
        scan_id: d.scan_id ?? candidateId,
        results_dir: d.scan_id ?? candidateId,
        started_at: d.started_at ?? null,
      })
    } catch (e) {
      console.error('Scan status refresh:', e)
    }
  }, [applyStatus])

  useEffect(() => {
    void tick()

    const onRefresh = () => {
      void tick()
    }

    const onEnv = (e: Event) => {
      const env = (e as CustomEvent<SseEnvelope>).detail
      if (!env || env.v !== 1) return
      if (env.type === 'scan_update' || env.type === 'queue_update') void tick()
    }

    const onVisible = () => {
      if (document.visibilityState === 'visible') void tick()
    }

    window.addEventListener(SSE_ENVELOPE_EVENT, onEnv)
    window.addEventListener(SCAN_STATUS_REFRESH_EVENT, onRefresh)
    document.addEventListener('visibilitychange', onVisible)

    const intervalId = window.setInterval(() => {
      if (activeRef.current) void tick()
    }, 15000)

    return () => {
      window.removeEventListener(SSE_ENVELOPE_EVENT, onEnv)
      window.removeEventListener(SCAN_STATUS_REFRESH_EVENT, onRefresh)
      document.removeEventListener('visibilitychange', onVisible)
      window.clearInterval(intervalId)
    }
  }, [tick])

  return scanStatus
}
