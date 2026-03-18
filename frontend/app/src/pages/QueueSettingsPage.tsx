import { Navigate } from 'react-router-dom'

/** @deprecated Use /admin/execution */
export default function QueueSettingsPage() {
  return <Navigate to="/admin/execution" replace />
}
