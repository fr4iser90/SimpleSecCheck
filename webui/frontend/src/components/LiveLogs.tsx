import { useEffect, useRef, useState } from 'react'

export default function LiveLogs() {
  const [logs, setLogs] = useState<string[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    let eventSource: EventSource | null = null
    let reconnectTimeout: number | null = null
    let reconnectAttempts = 0
    const maxReconnectAttempts = 10
    
    const connect = () => {
      console.log('[LiveLogs] Connecting to /api/scan/logs...')
      eventSource = new EventSource('/api/scan/logs')
      
      eventSource.onopen = () => {
        console.log('[LiveLogs] EventSource connected successfully')
        reconnectAttempts = 0 // Reset bei Erfolg
      }
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.line) {
            setLogs((prev) => [...prev, data.line])
          }
        } catch (err) {
          console.error('Failed to parse log line:', err, event.data)
        }
      }
      
      eventSource.onerror = (err) => {
        console.error('[LiveLogs] SSE error:', err)
        if (eventSource?.readyState === EventSource.CLOSED) {
          console.error('[LiveLogs] EventSource closed')
          eventSource.close()
          eventSource = null
          
          // Auto-reconnect mit exponential backoff
          if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000) // Max 30 Sekunden
            console.log(`[LiveLogs] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})...`)
            reconnectTimeout = setTimeout(connect, delay)
          } else {
            console.error('[LiveLogs] Max reconnection attempts reached')
          }
        }
      }
    }
    
    connect()
    
    return () => {
      console.log('[LiveLogs] Cleaning up EventSource connection')
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      if (eventSource) eventSource.close()
    }
  }, [])

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <button
          onClick={() => setAutoScroll(!autoScroll)}
          style={{ fontSize: '0.875rem', padding: '0.5rem 1rem' }}
        >
          {autoScroll ? '⏸️ Pause' : '▶️ Resume'} Auto-scroll
        </button>
        <span style={{ opacity: 0.7, fontSize: '0.875rem' }}>
          {logs.length} lines
        </span>
      </div>
      <div className="logs-container">
        {logs.length === 0 ? (
          <div style={{ opacity: 0.5 }}>Waiting for logs...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="log-line">
              {log}
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}
