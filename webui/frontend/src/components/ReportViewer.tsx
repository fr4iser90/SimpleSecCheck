import { useEffect, useState } from 'react'

interface ReportViewerProps {
  scanId?: string | null  // Optional: if provided, load report from /api/results/{scanId}/report
}

export default function ReportViewer({ scanId }: ReportViewerProps = {}) {
  const [reportUrl, setReportUrl] = useState<string | null>(null)

  useEffect(() => {
    // Determine which endpoint to use
    const reportEndpoint = scanId 
      ? `/api/results/${scanId}/report`
      : '/api/scan/report'
    
    // Fetch report URL
    fetch(reportEndpoint)
      .then((response) => {
        if (response.ok) {
          // Create blob URL for iframe
          response.blob().then((blob) => {
            const url = URL.createObjectURL(blob)
            setReportUrl(url)
          })
        } else {
          console.error('Failed to load report:', response.status, response.statusText)
        }
      })
      .catch((err) => {
        console.error('Failed to load report:', err)
      })
    
    // Cleanup blob URL on unmount
    return () => {
      if (reportUrl) {
        URL.revokeObjectURL(reportUrl)
      }
    }
  }, [scanId])

  if (!reportUrl) {
    return (
      <div style={{ 
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: 0.7 
      }}>
        Loading report...
      </div>
    )
  }

  return (
    <iframe
      src={reportUrl}
      style={{
        width: '100%',
        height: '100%',
        border: 'none',
        display: 'block',
      }}
      title="Security Report"
    />
  )
}
