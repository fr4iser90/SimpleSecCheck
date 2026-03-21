import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { resolveApiUrl } from '../utils/resolveApiUrl'
import type { SseEnvelope } from '../hooks/useGlobalSse'

const MAX_ROWS = 400

export default function AdminSseDebugPage() {
  const { isAuthenticated, user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [rows, setRows] = useState<SseEnvelope[]>([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  const clear = useCallback(() => setRows([]), [])

  useEffect(() => {
    if (!isAuthenticated || !isAdmin) return undefined

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
  }, [isAuthenticated, isAdmin])

  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="admin-settings-page">
        <div className="admin-settings-container">
          <h2>Access Denied</h2>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-settings-page">
      <div className="admin-settings-container">
        <p style={{ marginBottom: '1rem' }}>
          <Link to="/admin">← Admin</Link>
        </p>
        <h2>Live SSE events</h2>
        <p className="section-description" style={{ marginBottom: '1rem' }}>
          Raw <code style={{ fontSize: '0.9em' }}>event: ssc</code> envelopes for your session (newest first). Admin-only
          debug; closes when you leave this page.
        </p>
        <p style={{ marginBottom: '1rem', fontSize: '0.9rem' }}>
          Stream:{' '}
          <span
            style={{
              fontWeight: 600,
              color: connected ? 'var(--color-pass, #22c55e)' : 'var(--color-critical, #ef4444)',
            }}
          >
            {connected ? 'connected' : 'disconnected / reconnecting'}
          </span>
          {' · '}
          <button type="button" className="btn-secondary" onClick={clear}>
            Clear
          </button>
        </p>
        <div
          style={{
            maxHeight: '70vh',
            overflow: 'auto',
            fontFamily: 'ui-monospace, monospace',
            fontSize: '0.75rem',
            lineHeight: 1.45,
            background: 'var(--color-surface-muted, rgba(0,0,0,0.04))',
            borderRadius: 8,
            padding: '0.75rem',
          }}
        >
          {rows.length === 0 ? (
            <span style={{ opacity: 0.7 }}>Waiting for events…</span>
          ) : (
            rows.map((r, i) => (
              <pre
                key={`${i}-${r.type}-${JSON.stringify(r.payload).slice(0, 40)}`}
                style={{ margin: '0 0 0.75rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
              >
                {JSON.stringify(r, null, 2)}
              </pre>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
