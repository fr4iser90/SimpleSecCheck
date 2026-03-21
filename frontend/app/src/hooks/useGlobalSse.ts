import { useEffect, useRef } from 'react'
import { useAuth } from './useAuth'
import { resolveApiUrl } from '../utils/resolveApiUrl'

/** @deprecated Legacy custom event; UI should listen to SSE_ENVELOPE_EVENT. */
export const SSE_INVALIDATE_EVENT = 'ssc:invalidate'

/** Raw SSE envelope from `event: ssc` (detail = full object). */
export const SSE_ENVELOPE_EVENT = 'ssc:sse-envelope'

export type SseEnvelope = {
  v: number
  type: string
  scope: string
  payload: Record<string, unknown>
}

export type SseInvalidateScope = 'targets' | 'header' | 'all'

/**
 * One EventSource per signed-in user (cookies + same origin).
 * All server messages use `event: ssc` with JSON body `{ v, type, scope, payload }`.
 */
export function useGlobalSse(): void {
  const { isAuthenticated } = useAuth()
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!isAuthenticated) {
      esRef.current?.close()
      esRef.current = null
      return
    }

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
  }, [isAuthenticated])
}
