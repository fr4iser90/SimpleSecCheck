import type { ReactNode } from 'react'
import PageHeader from './PageHeader'
import PageCallout from './PageCallout'

interface AdminPageShellProps {
  title: string
  subtitle?: ReactNode
  callout?: ReactNode
  calloutTitle?: string
  actions?: ReactNode
  error?: string | null
  success?: string | null
  loading?: boolean
  loadingText?: string
  children?: ReactNode
}

export default function AdminPageShell({
  title,
  subtitle,
  callout,
  calloutTitle,
  actions,
  error,
  success,
  loading,
  loadingText = 'Loading…',
  children,
}: AdminPageShellProps) {
  return (
    <div className="container admin-page">
      <PageHeader title={title} subtitle={subtitle}>
        {actions}
      </PageHeader>
      {callout ? <PageCallout title={calloutTitle}>{callout}</PageCallout> : null}
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      {success && (
        <div className="success-message" role="alert">
          {success}
        </div>
      )}
      {loading ? (
        <div className="panel">
          <div className="panel__body loading">{loadingText}</div>
        </div>
      ) : (
        children
      )}
    </div>
  )
}
