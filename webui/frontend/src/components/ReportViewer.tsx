import { useEffect, useState } from 'react'

export default function ReportViewer() {
  const [reportUrl, setReportUrl] = useState<string | null>(null)

  useEffect(() => {
    // Fetch report URL
    fetch('/api/scan/report')
      .then((response) => {
        if (response.ok) {
          // Create blob URL for iframe
          response.blob().then((blob) => {
            const url = URL.createObjectURL(blob)
            setReportUrl(url)
          })
        }
      })
      .catch((err) => {
        console.error('Failed to load report:', err)
      })
  }, [])

  if (!reportUrl) {
    return <div style={{ opacity: 0.7 }}>Loading report...</div>
  }

  return (
    <div style={{ 
      border: '1px solid var(--glass-border-dark)', 
      borderRadius: '8px', 
      overflow: 'hidden',
      height: '80vh'
    }}>
      <iframe
        src={reportUrl}
        style={{
          width: '100%',
          height: '100%',
          border: 'none',
        }}
        title="Security Report"
      />
    </div>
  )
}
