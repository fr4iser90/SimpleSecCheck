import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { useConfig } from './hooks/useConfig'
import BootstrapLoader, { SetupStatus } from './components/BootstrapLoader'
import MainLayout from './components/MainLayout'
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
      {/* Admin Routes */}
      <Route path="/admin" element={
        <ProtectedRoute>
          <MainLayout>
            <AdminDashboardPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/settings" element={
        <ProtectedRoute>
          <MainLayout>
            <AdminSettingsPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/users" element={
        <ProtectedRoute>
          <MainLayout>
            <UserManagementPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/feature-flags" element={
        <ProtectedRoute>
          <MainLayout>
            <FeatureFlagsPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/auth" element={
        <ProtectedRoute>
          <MainLayout>
            <AuthSettingsPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/execution" element={
        <ProtectedRoute>
          <MainLayout>
            <ExecutionSettingsPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/queue" element={
        <ProtectedRoute>
          <MainLayout>
            <QueueSettingsPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/security" element={<Navigate to="/admin/policies" replace />} />
      <Route path="/admin/policies" element={
        <ProtectedRoute>
          <MainLayout>
            <AdminPoliciesPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/health" element={
        <ProtectedRoute>
          <MainLayout>
            <AdminHealthPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/sse-debug" element={
        <ProtectedRoute>
          <MainLayout>
            <AdminSseDebugPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/audit-log" element={
        <ProtectedRoute>
          <MainLayout>
            <AuditLogPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/security/ip-control" element={
        <ProtectedRoute>
          <MainLayout>
            <IPControlPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/scanner" element={
        <ProtectedRoute>
          <MainLayout>
            <ScannerManagementPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/tool-duration" element={
        <ProtectedRoute>
          <MainLayout>
            <AdminToolDurationPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/tool-settings" element={
        <ProtectedRoute>
          <MainLayout>
            <AdminScannerToolSettingsPage />
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/vulnerabilities" element={
        <ProtectedRoute>
          <MainLayout>
            <div style={{ padding: '2rem' }}>Vulnerability Database - Coming Soon</div>
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/scan-policies" element={
        <ProtectedRoute>
          <MainLayout>
            <div style={{ padding: '2rem' }}>Scan Policies - Coming Soon</div>
          </MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/notifications" element={
        <ProtectedRoute>
          <MainLayout>
            <div style={{ padding: '2rem' }}>Notification Management - Coming Soon</div>
          </MainLayout>
        </ProtectedRoute>
      } />
      {/* User Routes */}
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
