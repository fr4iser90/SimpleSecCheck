import { useEffect, useRef, useState } from 'react'

export default function LiveLogs() {
  const [logs, setLogs] = useState<string[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    // Use SSE instead of polling for real-time updates
    const eventSource = new EventSource('/api/scan/stream')
    
    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        
        if (data.error) {
          console.error('[LiveLogs] SSE error:', data.error)
          return
        }
        
        // Update logs from SSE data (all log lines)
        if (data.logs && Array.isArray(data.logs)) {
          setLogs(data.logs)
        }
      } catch (err) {
        console.error('[LiveLogs] Failed to parse SSE data:', err)
      }
    }
    
    eventSource.onerror = (error) => {
      console.error('[LiveLogs] SSE connection error:', error)
      eventSource.close()
    }
    
    return () => {
      eventSource.close()
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
