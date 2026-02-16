import { useEffect, useRef, useState } from 'react'

export default function LiveLogs() {
  const [logs, setLogs] = useState<string[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    let ws: WebSocket | null = null
    let reconnectTimeout: number | null = null
    let reconnectAttempts = 0
    const maxReconnectAttempts = 10
    
    const connect = () => {
      // Convert HTTP to WebSocket URL
      const wsUrl = window.location.origin.replace(/^http/, 'ws') + '/api/scan/logs/ws'
      console.log('[LiveLogs] Connecting to WebSocket:', wsUrl)
      
      try {
        ws = new WebSocket(wsUrl)
        
        ws.onopen = () => {
          console.log('[LiveLogs] WebSocket connected successfully')
          reconnectAttempts = 0 // Reset on success
        }
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'log' && data.data) {
              setLogs((prev) => [...prev, data.data])
            } else if (data.type === 'ping') {
              // Ignore ping messages
              return
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err, event.data)
          }
        }
        
        ws.onerror = (err) => {
          console.error('[LiveLogs] WebSocket error:', err)
        }
        
        ws.onclose = (event) => {
          console.log('[LiveLogs] WebSocket closed:', event.code, event.reason)
          ws = null
          
          // Auto-reconnect with exponential backoff
          if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000) // Max 30 seconds
            console.log(`[LiveLogs] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})...`)
            reconnectTimeout = setTimeout(connect, delay)
          } else {
            console.error('[LiveLogs] Max reconnection attempts reached')
          }
        }
      } catch (err) {
        console.error('[LiveLogs] Failed to create WebSocket:', err)
        // Retry after delay
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
          reconnectTimeout = setTimeout(connect, delay)
        }
      }
    }
    
    connect()
    
    return () => {
      console.log('[LiveLogs] Cleaning up WebSocket connection')
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      if (ws) {
        ws.close()
        ws = null
      }
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
