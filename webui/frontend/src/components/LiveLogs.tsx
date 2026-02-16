import { useEffect, useRef, useState } from 'react'

export default function LiveLogs() {
  const [logs, setLogs] = useState<string[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    let pollInterval: number | null = null
    let lastCount = 0
    
    const fetchLogs = async () => {
      try {
        const response = await fetch('/api/scan/logs')
        if (!response.ok) {
          console.error('[LiveLogs] Failed to fetch logs:', response.status)
          return
        }
        
        const data = await response.json()
        if (data.lines && Array.isArray(data.lines)) {
          // Only update if we have new lines
          if (data.lines.length > lastCount) {
            setLogs(data.lines)
            lastCount = data.lines.length
          }
        }
      } catch (err) {
        console.error('[LiveLogs] Error fetching logs:', err)
      }
    }
    
    // Fetch immediately
    fetchLogs()
    
    // Poll every 500ms for real-time updates
    pollInterval = window.setInterval(fetchLogs, 500)
    
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval)
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
