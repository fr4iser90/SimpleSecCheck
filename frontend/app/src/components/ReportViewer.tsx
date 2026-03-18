import { useEffect, useState } from 'react'
import { useConfig } from '../hooks/useConfig'
import { getReportEndpoint } from '../utils/apiEndpoints'

interface ReportViewerProps {
  scanId?: string | null  // Optional: if provided, load report from /api/results/{scanId}/report
}

export default function ReportViewer({ scanId }: ReportViewerProps = {}) {
  const { config } = useConfig()
  const [reportUrl, setReportUrl] = useState<string | null>(null)

  useEffect(() => {
    // Determine which endpoint to use
    const reportEndpoint = getReportEndpoint(scanId, config)

    const fetchReport = async (endpoint: string, fallbackEndpoint?: string) => {
      try {
        const response = await fetch(endpoint)
        if (response.ok) {
          const blob = await response.blob()
          const url = URL.createObjectURL(blob)
          setReportUrl(url)
          return
        }

        // If primary report URL denies access, fall back to session-safe route
        if (response.status === 403 && fallbackEndpoint) {
          console.warn('Report endpoint denied, retrying with session-safe endpoint')
          await fetchReport(fallbackEndpoint)
          return
        }

        console.error('Failed to load report:', response.status, response.statusText)
      } catch (err) {
        console.error('Failed to load report:', err)
      }
    }

    const sessionFallback = scanId ? `/api/my-results/${scanId}/report` : undefined
    fetchReport(reportEndpoint, sessionFallback)
    
    // Cleanup blob URL on unmount
    return () => {
      if (reportUrl) {
        URL.revokeObjectURL(reportUrl)
      }
    }
  }, [scanId, config?.features.session_management])

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
