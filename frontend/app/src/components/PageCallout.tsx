import type { ReactNode } from 'react'

interface PageCalloutProps {
  title?: string
  children: ReactNode
}

/** Short contextual help below page headers (admin / settings). */
export default function PageCallout({ title, children }: PageCalloutProps) {
  return (
    <aside className="page-callout" aria-label={title}>
      {title ? <div className="page-callout__title">{title}</div> : null}
      <div className="page-callout__body">{children}</div>
    </aside>
  )
}
