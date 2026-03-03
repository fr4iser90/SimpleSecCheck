import { useEffect, useRef, useState } from 'react'

interface LiveLogsProps {
  scanId?: string
  isActive?: boolean
}

export default function LiveLogs({ scanId, isActive = false }: LiveLogsProps) {
  const [logs, setLogs] = useState<string[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    // Only connect if scan is active and scanId is provided
    if (!isActive || !scanId) {
      return
    }
    
    let ws: WebSocket | null = null
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
    let heartbeatInterval: ReturnType<typeof setInterval> | null = null
    let reconnectAttempts = 0
    const maxReconnectAttempts = 10
    const reconnectDelay = 3000
    
    const connect = () => {
      try {
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/scan/stream?scan_id=${scanId}`
        ws = new WebSocket(wsUrl)
        
        ws.onopen = () => {
          console.log('[LiveLogs] WebSocket connected')
          reconnectAttempts = 0
          
          heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send('ping')
            }
          }, 25000)
        }
        
        ws.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data)
            
            if (data.error) {
              console.error('[LiveLogs] WebSocket error:', data.error)
              return
            }
            
            // Note: Backend sends logs: [] (empty) for security
            // LiveLogs component shows "0 lines" intentionally
            if (data.logs && Array.isArray(data.logs)) {
              setLogs(data.logs)
            }
          } catch (err) {
            console.error('[LiveLogs] Failed to parse WebSocket data:', err)
          }
        }
        
        ws.onerror = (error) => {
          console.error('[LiveLogs] WebSocket error:', error)
        }
        
        ws.onclose = () => {
          console.log('[LiveLogs] WebSocket closed')
          
          if (heartbeatInterval) {
            clearInterval(heartbeatInterval)
            heartbeatInterval = null
          }
          
          if (reconnectAttempts < maxReconnectAttempts && isActive) {
            reconnectAttempts++
            reconnectTimeout = setTimeout(() => {
              connect()
            }, reconnectDelay)
          }
        }
      } catch (error) {
        console.error('[LiveLogs] WebSocket connection error:', error)
      }
    }
    
    connect()
    
    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
      }
      if (heartbeatInterval) {
        clearInterval(heartbeatInterval)
      }
      if (ws) {
        ws.close()
      }
    }
  }, [scanId, isActive])

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
