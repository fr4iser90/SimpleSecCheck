import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { useGlobalSse } from '../hooks/useGlobalSse'
import AppSidebar from './AppSidebar'
import AppTopbar from './AppTopbar'

const WIDE_PATHS = /^\/(scan|bulk|queue)(\/|$)/

export default function MainLayout({ children }: { children: ReactNode }) {
  useGlobalSse()
  const { pathname } = useLocation()
  const wide = WIDE_PATHS.test(pathname)

  return (
    <div className="app-shell">
      <AppSidebar />
      <div className="app-shell__main">
        <AppTopbar />
        <div className="app-shell__content shell-content">
          <div className={`app-shell__page${wide ? ' app-shell__page--wide' : ''}`}>{children}</div>
        </div>
      </div>
    </div>
  )
}
