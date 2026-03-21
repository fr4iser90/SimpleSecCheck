import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './hooks/useAuth'
import BootstrapLoader, { SetupStatus } from './components/BootstrapLoader'
import MainLayout from './components/MainLayout'
import { ProtectedRoute, AdminRoute } from './components/RouteGuards'
import HomePage from './pages/HomePage'
import ScanView from './pages/ScanView'
import BatchProgressPage from './pages/BatchProgressPage'
import QueueView from './pages/QueueView'
import MyScansPage from './pages/MyScansPage'
import StatisticsPage from './pages/StatisticsPage'
import SetupWizard from './pages/SetupWizard'
import LoginPage from './pages/LoginPage'
import SignUpPage from './pages/SignUpPage'
import VerifyEmailPage from './pages/VerifyEmailPage'
import CapabilitiesPage from './pages/CapabilitiesPage'
import PasswordResetPage from './pages/PasswordResetPage'
import AdminDashboardPage from './pages/AdminDashboardPage'
import AdminSettingsPage from './pages/AdminSettingsPage'
import AuditLogPage from './pages/AuditLogPage'
import UserManagementPage from './pages/UserManagementPage'
import FeatureFlagsPage from './pages/FeatureFlagsPage'
import AuthSettingsPage from './pages/AuthSettingsPage'
import QueueSettingsPage from './pages/QueueSettingsPage'
import ExecutionSettingsPage from './pages/ExecutionSettingsPage'
import AdminHealthPage from './pages/AdminHealthPage'
import AdminSseDebugPage from './pages/AdminSseDebugPage'
import AdminPoliciesPage from './pages/AdminPoliciesPage'
import IPControlPage from './pages/IPControlPage'
import ScannerManagementPage from './pages/ScannerManagementPage'
import AdminToolDurationPage from './pages/AdminToolDurationPage'
import AdminScannerToolSettingsPage from './pages/AdminScannerToolSettingsPage'
import ProfilePage from './pages/ProfilePage'
import APIKeysPage from './pages/APIKeysPage'
import MyTargetsPage from './pages/MyTargetsPage'
import Footer from './components/Footer'
import './App.css'

/**
 * Application Routes Component
 * Renders routes based on setup status
 */
function AppRoutes({ setupStatus }: { setupStatus: SetupStatus }) {
  // If setup is not complete, redirect all routes to /setup
  if (!setupStatus.setup_complete) {
    return (
      <Routes>
        <Route
          path="/setup"
          element={
            <div className="shell-content">
              <SetupWizard />
            </div>
          }
        />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Routes>
    )
  }

  // Setup is complete - show normal application routes
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <div className="shell-content">
            <LoginPage />
          </div>
        }
      />
      <Route
        path="/signup"
        element={
          <div className="shell-content">
            <SignUpPage />
          </div>
        }
      />
      <Route
        path="/verify-email"
        element={
          <div className="shell-content">
            <VerifyEmailPage />
          </div>
        }
      />
      <Route path="/capabilities" element={
        <MainLayout>
          <CapabilitiesPage />
        </MainLayout>
      } />
      <Route
        path="/password-reset"
        element={
          <div className="shell-content">
            <PasswordResetPage />
          </div>
        }
      />
      <Route path="/" element={
        <ProtectedRoute>
          <MainLayout>
            <HomePage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/scan" element={
        <ProtectedRoute>
          <MainLayout>
            <ScanView />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/bulk" element={
        <ProtectedRoute>
          <MainLayout>
            <BatchProgressPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/queue" element={
        <ProtectedRoute>
          <MainLayout>
            <QueueView />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/my-scans" element={
        <ProtectedRoute>
          <MainLayout>
            <MyScansPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/statistics" element={
        <ProtectedRoute>
          <MainLayout>
            <StatisticsPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      {/* Admin Routes — AdminRoute = login + role admin (see RouteGuards) */}
      <Route path="/admin" element={
        <AdminRoute>
          <MainLayout>
            <AdminDashboardPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/settings" element={
        <AdminRoute>
          <MainLayout>
            <AdminSettingsPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/users" element={
        <AdminRoute>
          <MainLayout>
            <UserManagementPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/feature-flags" element={
        <AdminRoute>
          <MainLayout>
            <FeatureFlagsPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/auth" element={
        <AdminRoute>
          <MainLayout>
            <AuthSettingsPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/execution" element={
        <AdminRoute>
          <MainLayout>
            <ExecutionSettingsPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/queue" element={
        <AdminRoute>
          <MainLayout>
            <QueueSettingsPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/security" element={<Navigate to="/admin/policies" replace />} />
      <Route path="/admin/policies" element={
        <AdminRoute>
          <MainLayout>
            <AdminPoliciesPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/health" element={
        <AdminRoute>
          <MainLayout>
            <AdminHealthPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/sse-debug" element={
        <AdminRoute>
          <MainLayout>
            <AdminSseDebugPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/audit-log" element={
        <AdminRoute>
          <MainLayout>
            <AuditLogPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/security/ip-control" element={
        <AdminRoute>
          <MainLayout>
            <IPControlPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/scanner" element={
        <AdminRoute>
          <MainLayout>
            <ScannerManagementPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/tool-duration" element={
        <AdminRoute>
          <MainLayout>
            <AdminToolDurationPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/tool-settings" element={
        <AdminRoute>
          <MainLayout>
            <AdminScannerToolSettingsPage />
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/vulnerabilities" element={
        <AdminRoute>
          <MainLayout>
            <div style={{ padding: '2rem' }}>Vulnerability Database - Coming Soon</div>
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/scan-policies" element={
        <AdminRoute>
          <MainLayout>
            <div style={{ padding: '2rem' }}>Scan Policies - Coming Soon</div>
          </MainLayout>
        </AdminRoute>
      } />
      <Route path="/admin/notifications" element={
        <AdminRoute>
          <MainLayout>
            <div style={{ padding: '2rem' }}>Notification Management - Coming Soon</div>
          </MainLayout>
        </AdminRoute>
      } />
      {/* User Routes — ProtectedRoute = instance login policy only */}
      <Route path="/profile" element={
        <ProtectedRoute>
          <MainLayout>
            <ProfilePage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/my-targets" element={
        <ProtectedRoute>
          <MainLayout>
            <MyTargetsPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/api-keys" element={
        <ProtectedRoute>
          <MainLayout>
            <APIKeysPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      {/* Redirect /setup to / if setup is already complete */}
      <Route path="/setup" element={<Navigate to="/" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

/**
 * Main Application Component
 * Uses BootstrapLoader to check setup status before rendering routes
 */
function AppContent() {
  return (
    <BootstrapLoader>
      {(setupStatus) => (
        <BrowserRouter>
          <div className="app">
            <div className="app__body">
              <AppRoutes setupStatus={setupStatus} />
            </div>
            {setupStatus.setup_complete ? <Footer /> : null}
          </div>
        </BrowserRouter>
      )}
    </BootstrapLoader>
  )
}

/**
 * Root App Component
 * Wraps application with AuthProvider
 */
function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
