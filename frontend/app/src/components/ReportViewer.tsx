import { useEffect, useState, useRef, useCallback } from 'react'
import { useConfig } from '../hooks/useConfig'
import { getReportEndpoint } from '../utils/apiEndpoints'

const COPY_SHARE_MSG = 'SSC_COPY_SHARE_LINK'

interface ReportViewerProps {
  scanId?: string | null // Optional: if provided, load report from /api/results/{scanId}/report
}

export default function ReportViewer({ scanId }: ReportViewerProps = {}) {
  const { config } = useConfig()
  const [reportUrl, setReportUrl] = useState<string | null>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const handleCopyShareFromIframe = useCallback(async () => {
    const sid = scanId
    if (!sid) return
    try {
      const { apiFetch } = await import('../utils/apiClient')
      const res = await apiFetch(`/api/v1/scans/${sid}/report-share-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ regenerate: false }),
      })
      if (!res.ok) {
        let msg = `Share link failed (${res.status})`
        try {
          const j = await res.json()
          const d = j.detail
          msg = typeof d === 'string' ? d : Array.isArray(d) ? String(d[0]?.msg ?? msg) : msg
        } catch {
          /* ignore */
        }
        throw new Error(msg)
      }
      const data = (await res.json()) as { share_path: string }
      await navigator.clipboard.writeText(`${window.location.origin}${data.share_path}`)
      window.alert('Share link copied. Anyone with the link can view this report.')
    } catch (e) {
      window.alert(e instanceof Error ? e.message : 'Could not copy share link')
    }
  }, [scanId])

  useEffect(() => {
    if (!scanId || !reportUrl) return
    const onMessage = (ev: MessageEvent) => {
      if (!ev.data || ev.data.type !== COPY_SHARE_MSG) return
      if (iframeRef.current?.contentWindow !== ev.source) return
      void handleCopyShareFromIframe()
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [scanId, reportUrl, handleCopyShareFromIframe])

  useEffect(() => {
    const reportEndpoint = getReportEndpoint(scanId, config)

    const fetchReport = async (endpoint: string) => {
      try {
        const response = await fetch(endpoint, { credentials: 'include' })
        if (response.ok) {
          const blob = await response.blob()
          const url = URL.createObjectURL(blob)
          setReportUrl(url)
          return
        }
        console.error('Failed to load report:', response.status, response.statusText)
      } catch (err) {
        console.error('Failed to load report:', err)
      }
    }
    fetchReport(reportEndpoint)

    return () => {
      setReportUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return null
      })
    }
  }, [scanId, config?.features.session_management])

  if (!reportUrl) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: 0.7,
        }}
      >
        Loading report...
      </div>
    )
  }

  return (
    <iframe
      ref={iframeRef}
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
