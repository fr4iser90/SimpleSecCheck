import { useEffect, useRef } from 'react'
import { resolveApiUrl } from '../utils/resolveApiUrl'

/** Raw SSE envelope from `event: ssc` (detail = full object). */
export const SSE_ENVELOPE_EVENT = 'ssc:sse-envelope'

export type SseEnvelope = {
  v: number
  type: string
  scope: string
  payload: Record<string, unknown>
}

/**
 * One EventSource per browser session (user JWT or guest session_id cookie).
 * All server messages use `event: ssc` with JSON body `{ v, type, scope, payload }`.
 */
export function useGlobalSse(): void {
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const url = resolveApiUrl('/api/v1/events/stream')
    const es = new EventSource(url, { withCredentials: true })
    esRef.current = es

    const onSsc = (ev: MessageEvent) => {
      try {
        const raw = JSON.parse(ev.data) as SseEnvelope
        if (raw?.v !== 1 || !raw.type) return
        window.dispatchEvent(new CustomEvent(SSE_ENVELOPE_EVENT, { detail: raw }))
      } catch {
        /* ignore */
      }
    }

    es.addEventListener('ssc', onSsc as EventListener)

    return () => {
      es.removeEventListener('ssc', onSsc as EventListener)
      es.close()
      esRef.current = null
    }
  }, [])
}
