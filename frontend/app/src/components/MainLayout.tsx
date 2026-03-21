import type { ReactNode } from 'react'
import Header from './Header'

/**
 * Main content area of the app shell (header + this scroll region); pages use `.container` inside.
 */
export default function MainLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Header />
      <div className="shell-content">{children}</div>
    </>
  )
}
