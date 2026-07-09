import { useEffect, useRef, type ReactNode } from 'react'
import PageHeader from './PageHeader'
import PageCallout from './PageCallout'
import { useToast } from '../context/ToastContext'

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
  const toast = useToast()
  const prevSuccess = useRef<string | null>(null)
  const prevError = useRef<string | null>(null)

  useEffect(() => {
    if (success && success !== prevSuccess.current) {
      toast.success(success)
      prevSuccess.current = success
    } else if (!success) {
      prevSuccess.current = null
    }
  }, [success, toast])

  useEffect(() => {
    if (error && error !== prevError.current) {
      toast.error(error)
      prevError.current = error
    } else if (!error) {
      prevError.current = null
    }
  }, [error, toast])

  return (
    <div className="container admin-page">
      <PageHeader title={title} subtitle={subtitle}>
        {actions}
      </PageHeader>
      {callout ? <PageCallout title={calloutTitle}>{callout}</PageCallout> : null}
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
