import type { ReactNode } from 'react'

interface AdminPanelProps {
  title?: string
  description?: ReactNode
  toolbar?: ReactNode
  flush?: boolean
  children: ReactNode
}

export default function AdminPanel({ title, description, toolbar, flush, children }: AdminPanelProps) {
  return (
    <div className="panel">
      {(title || description) && (
        <div className="panel__header">
          <div>
            {title && <h2 className="panel__title">{title}</h2>}
            {description && <p className="panel__desc">{description}</p>}
          </div>
        </div>
      )}
      {toolbar}
      <div className={`panel__body${flush ? ' panel__body--flush' : ''}`}>{children}</div>
    </div>
  )
}
