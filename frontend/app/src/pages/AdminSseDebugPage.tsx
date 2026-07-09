import { useState, useEffect, useRef, useCallback } from 'react'
import AdminPageShell from '../components/AdminPageShell'
import AdminPanel from '../components/AdminPanel'
import { resolveApiUrl } from '../utils/resolveApiUrl'
import type { SseEnvelope } from '../hooks/useGlobalSse'

const MAX_ROWS = 400

export default function AdminSseDebugPage() {
  const [rows, setRows] = useState<SseEnvelope[]>([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  const clear = useCallback(() => setRows([]), [])

  useEffect(() => {
    const url = resolveApiUrl('/api/v1/events/stream')
    const es = new EventSource(url, { withCredentials: true })
    esRef.current = es

    const push = (env: SseEnvelope) => {
      setRows((prev) => {
        const next = [env, ...prev]
        return next.length > MAX_ROWS ? next.slice(0, MAX_ROWS) : next
      })
    }

    const onOpen = () => setConnected(true)
    const onError = () => setConnected(false)
    const onSsc = (ev: MessageEvent) => {
      try {
        const raw = JSON.parse(ev.data) as SseEnvelope
        if (raw?.v === 1) push(raw)
      } catch {
        /* ignore */
      }
    }

    es.addEventListener('open', onOpen)
    es.addEventListener('error', onError)
    es.addEventListener('ssc', onSsc as EventListener)

    return () => {
      es.removeEventListener('open', onOpen)
      es.removeEventListener('error', onError)
      es.removeEventListener('ssc', onSsc as EventListener)
      es.close()
      esRef.current = null
      setConnected(false)
    }
  }, [])

  return (
    <AdminPageShell
      title="Live SSE events"
      subtitle={
        <>
          Raw <code>event: ssc</code> envelopes for your session (newest first). Admin-only debug; closes when you
          leave this page.
        </>
      }
      actions={
        <button type="button" className="btn-secondary" onClick={clear}>
          Clear
        </button>
      }
    >
      <AdminPanel
        title="Event stream"
        description={
          <span>
            Stream:{' '}
            <span
              style={{
                fontWeight: 600,
                color: connected ? 'var(--ds-success)' : 'var(--ds-error)',
              }}
            >
              {connected ? 'connected' : 'disconnected / reconnecting'}
            </span>
          </span>
        }
        flush
      >
        <div className="code-stream">
          {rows.length === 0 ? (
            <span style={{ opacity: 0.7 }}>Waiting for events…</span>
          ) : (
            rows.map((r, i) => (
              <pre key={`${i}-${r.type}-${JSON.stringify(r.payload).slice(0, 40)}`}>
                {JSON.stringify(r, null, 2)}
              </pre>
            ))
          )}
        </div>
      </AdminPanel>
    </AdminPageShell>
  )
}
