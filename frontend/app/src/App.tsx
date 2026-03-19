import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { useConfig } from './hooks/useConfig'
import BootstrapLoader, { SetupStatus } from './components/BootstrapLoader'
import Header from './components/Header'
import ThemeToggle from './components/ThemeToggle'
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
import AdminPoliciesPage from './pages/AdminPoliciesPage'
import IPControlPage from './pages/IPControlPage'
import ScannerManagementPage from './pages/ScannerManagementPage'
import AdminToolDurationPage from './pages/AdminToolDurationPage'
import AdminScannerToolSettingsPage from './pages/AdminScannerToolSettingsPage'
import ProfilePage from './pages/ProfilePage'
import APIKeysPage from './pages/APIKeysPage'
import MyTargetsPage from './pages/MyTargetsPage'
import './App.css'

/**
 * Protected Route Component
 * 
 * Note: This component does NOT wait for useConfig() during bootstrap.
 * Config loading happens after setup is complete, so auth_mode is checked
 * from config when available, but doesn't block rendering.
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const { config } = useConfig()

  // Show loading only if auth is loading (config loading is non-blocking)
  if (authLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #007bff',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }}></div>
        <p style={{ color: '#666', fontSize: '16px' }}>Loading...</p>
      </div>
    )
  }

  // FREE mode: no authentication required
  // If config is still loading, allow access (config loads after setup, so if we're here, setup is complete)
  // Admin can always login if they want, but it's never required in free mode
  if (!config || config.auth_mode === 'free' || !config.login_required) {
    return <>{children}</>
  }

  // BASIC/JWT mode: authentication required
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

/**
 * Application Routes Component
 * Renders routes based on setup status
 */
function AppRoutes({ setupStatus }: { setupStatus: SetupStatus }) {
  // If setup is not complete, redirect all routes to /setup
  if (!setupStatus.setup_complete) {
    return (
      <Routes>
        <Route path="/setup" element={<SetupWizard />} />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Routes>
    )
  }

  // Setup is complete - show normal application routes
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignUpPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/capabilities" element={<CapabilitiesPage />} />
      <Route path="/password-reset" element={<PasswordResetPage />} />
      <Route path="/" element={
        <ProtectedRoute>
          <Header />
          <HomePage />
        </ProtectedRoute>
      } />
      <Route path="/scan" element={
        <ProtectedRoute>
          <Header />
          <ScanView />
        </ProtectedRoute>
      } />
      <Route path="/bulk" element={
        <ProtectedRoute>
          <Header />
          <BatchProgressPage />
        </ProtectedRoute>
      } />
      <Route path="/queue" element={
        <ProtectedRoute>
          <Header />
          <QueueView />
        </ProtectedRoute>
      } />
      <Route path="/my-scans" element={
        <ProtectedRoute>
          <Header />
          <MyScansPage />
        </ProtectedRoute>
      } />
      <Route path="/statistics" element={
        <ProtectedRoute>
          <Header />
          <StatisticsPage />
        </ProtectedRoute>
      } />
      {/* Admin Routes */}
      <Route path="/admin" element={
        <ProtectedRoute>
          <Header />
          <AdminDashboardPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/settings" element={
        <ProtectedRoute>
          <Header />
          <AdminSettingsPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/users" element={
        <ProtectedRoute>
          <Header />
          <UserManagementPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/feature-flags" element={
        <ProtectedRoute>
          <Header />
          <FeatureFlagsPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/auth" element={
        <ProtectedRoute>
          <Header />
          <AuthSettingsPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/execution" element={
        <ProtectedRoute>
          <Header />
          <ExecutionSettingsPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/queue" element={
        <ProtectedRoute>
          <Header />
          <QueueSettingsPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/security" element={<Navigate to="/admin/policies" replace />} />
      <Route path="/admin/policies" element={
        <ProtectedRoute>
          <Header />
          <AdminPoliciesPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/health" element={
        <ProtectedRoute>
          <Header />
          <AdminHealthPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/audit-log" element={
        <ProtectedRoute>
          <Header />
          <AuditLogPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/security/ip-control" element={
        <ProtectedRoute>
          <Header />
          <IPControlPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/scanner" element={
        <ProtectedRoute>
          <Header />
          <ScannerManagementPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/tool-duration" element={
        <ProtectedRoute>
          <Header />
          <AdminToolDurationPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/tool-settings" element={
        <ProtectedRoute>
          <Header />
          <AdminScannerToolSettingsPage />
        </ProtectedRoute>
      } />
      <Route path="/admin/vulnerabilities" element={
        <ProtectedRoute>
          <Header />
          <div style={{ padding: '2rem' }}>Vulnerability Database - Coming Soon</div>
        </ProtectedRoute>
      } />
      <Route path="/admin/scan-policies" element={
        <ProtectedRoute>
          <Header />
          <div style={{ padding: '2rem' }}>Scan Policies - Coming Soon</div>
        </ProtectedRoute>
      } />
      <Route path="/admin/notifications" element={
        <ProtectedRoute>
          <Header />
          <div style={{ padding: '2rem' }}>Notification Management - Coming Soon</div>
        </ProtectedRoute>
      } />
      <Route path="/admin/health" element={
        <ProtectedRoute>
          <Header />
          <div style={{ padding: '2rem' }}>System Health - Coming Soon</div>
        </ProtectedRoute>
      } />
      {/* User Routes */}
      <Route path="/profile" element={
        <ProtectedRoute>
          <Header />
          <ProfilePage />
        </ProtectedRoute>
      } />
      <Route path="/my-targets" element={
        <ProtectedRoute>
          <Header />
          <MyTargetsPage />
        </ProtectedRoute>
      } />
      <Route path="/api-keys" element={
        <ProtectedRoute>
          <Header />
          <APIKeysPage />
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
            <ThemeToggle />
            <AppRoutes setupStatus={setupStatus} />
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
