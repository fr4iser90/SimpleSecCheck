import { useEffect, useRef, useState } from 'react'

export default function LiveLogs() {
  const [logs, setLogs] = useState<string[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    const eventSource = new EventSource('/api/scan/logs')

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.line) {
          setLogs((prev) => [...prev, data.line])
        }
      } catch (err) {
        console.error('Failed to parse log line:', err)
      }
    }

    eventSource.onerror = (err) => {
      console.error('SSE error:', err)
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
