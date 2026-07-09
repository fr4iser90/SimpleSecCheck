import { useEffect, useRef } from 'react'
import { SSE_ENVELOPE_EVENT, type SseEnvelope } from './useGlobalSse'

/** Run a callback when matching SSE envelope types arrive (push-driven refresh). */
export function useSseRefresh(types: string[], onEvent: (env: SseEnvelope) => void): void {
  const typesKey = types.join('|')
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    const allowed = new Set(types)
    const onMessage = (e: Event) => {
      const env = (e as CustomEvent<SseEnvelope>).detail
      if (!env || env.v !== 1) return
      if (!allowed.has(env.type)) return
      handlerRef.current(env)
    }
    window.addEventListener(SSE_ENVELOPE_EVENT, onMessage)
    return () => window.removeEventListener(SSE_ENVELOPE_EVENT, onMessage)
  }, [typesKey])
}
