import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface SetupStatus {
  setup_required: boolean
  setup_complete: boolean
  database_connected: boolean
  tables_exist: Record<string, boolean>
  admin_exists: boolean
  system_state_exists: boolean
}

interface AdminUser {
  username: string
  email: string
  password: string
  password_confirm: string
}

interface SystemConfig {
  auth_mode: string
  scanner_timeout: number
  max_concurrent_scans: number
  smtp?: {
    enabled: boolean
    host: string
    port: number
    user: string
    password: string
    use_tls: boolean
    from_email: string
    from_name: string
  }
}

export default function SetupWizard() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [step, setStep] = useState(0) // Start with token verification step
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null)
  const [setupToken, setSetupToken] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(
    sessionStorage.getItem('setup_session_id')
  )
  
  const [adminUser, setAdminUser] = useState<AdminUser>({
    username: '',
    email: '',
    password: '',
    password_confirm: ''
  })
  
  const [useCase, setUseCase] = useState<string>('')
  const [systemConfig, setSystemConfig] = useState<SystemConfig>({
    auth_mode: 'free',
    scanner_timeout: 3600,
    max_concurrent_scans: 5,
    smtp: {
      enabled: false,
      host: 'smtp.gmail.com',
      port: 587,
      user: '',
      password: '',
      use_tls: true,
      from_email: 'noreply@simpleseccheck.local',
      from_name: 'SimpleSecCheck'
    }
  })

  // Check setup status on component mount
  useEffect(() => {
    checkSetupStatus()
  }, [])

  const checkSetupStatus = async () => {
    try {
      setLoading(true)
      
      // If we have a session, use it to check status
      if (sessionId) {
        await validateSession()
        return
      }
      
      // No session yet - check if setup is already complete (public info)
      // This allows redirecting if setup is done, without requiring token
      try {
        const response = await fetch('/api/setup/status')
        if (response.ok) {
          const data = await response.json()
          if (data.setup_complete) {
            // Setup is complete, redirect to home
            navigate('/')
            return
          }
        }
      } catch (err) {
        // Status check failed (probably 401 because setup not complete)
        // This is expected - show token input
      }
      
      // No session and setup not complete - show token input
      setStep(0)
    } catch (err) {
      console.error('Setup status check failed:', err)
      setStep(0)
    } finally {
      setLoading(false)
    }
  }

  const validateSession = async () => {
    if (!sessionId) return
    
    try {
      setLoading(true)
      // Validate session by checking setup status WITH session header
      const response = await fetch('/api/setup/status', {
        headers: {
          'X-Setup-Session': sessionId
        }
      })
      
      if (!response.ok) {
        // Session invalid or expired, clear it and show token step
        sessionStorage.removeItem('setup_session_id')
        setSessionId(null)
        setStep(0)
        setError('Your setup session has expired. Please enter the setup token again.')
        return
      }
      
      const data = await response.json()
      setSetupStatus(data)
      
      // If setup is already complete, redirect
      if (data.setup_complete) {
        sessionStorage.removeItem('setup_session_id')
        setSessionId(null)
        navigate('/')
        return
      }
      
      // Session is valid, skip token step
      setStep(1)
    } catch (err) {
      // Session validation failed, clear it and show token step
      sessionStorage.removeItem('setup_session_id')
      setSessionId(null)
      setStep(0)
      setError('Session validation failed. Please enter the setup token again.')
      console.error('Session validation failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyToken = async () => {
    if (!setupToken.trim()) {
      setError('Please enter a setup token')
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch('/api/setup/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Setup-Token': setupToken.trim()
        }
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Invalid token' }))
        throw new Error(errorData.detail || 'Token verification failed')
      }
      
      const data = await response.json()
      
      if (data.session_id) {
        // Store session ID
        sessionStorage.setItem('setup_session_id', data.session_id)
        setSessionId(data.session_id)
        
        // Fetch setup status with session to get real values
        try {
          const statusResponse = await fetch('/api/setup/status', {
            headers: {
              'X-Setup-Session': data.session_id
            }
          })
          if (statusResponse.ok) {
            const statusData = await statusResponse.json()
            setSetupStatus(statusData)
          }
        } catch (statusErr) {
          console.error('Failed to fetch setup status after token verification:', statusErr)
        }
        
        setStep(1) // Move to first setup step
      } else {
        throw new Error('No session ID received')
      }
    } catch (err: any) {
      setError(err.message || 'Token verification failed. Please check your token.')
      console.error('Token verification failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleNext = () => {
    if (step < 4) {
      setStep(step + 1)
    }
  }
  
  const handleUseCaseSelect = (selectedUseCase: string) => {
    setUseCase(selectedUseCase)
    // Apply intelligent defaults based on use case
    const useCaseConfigs: Record<string, Partial<SystemConfig>> = {
      solo: {
        auth_mode: 'free',
      },
      network_intern: {
        auth_mode: 'basic',
      },
      public_web: {
        auth_mode: 'free',
      },
      enterprise: {
        auth_mode: 'jwt',
      },
    }
    
    const config = useCaseConfigs[selectedUseCase]
    if (config) {
      setSystemConfig({
        ...systemConfig,
        ...config,
      })
    }
  }

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1)
    }
  }

  const handleAdminUserChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAdminUser({
      ...adminUser,
      [e.target.name]: e.target.value
    })
  }

  const handleSystemConfigChange = (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target
    const checked = (e.target as HTMLInputElement).checked
    
    if (name.startsWith('smtp.')) {
      const smtpKey = name.replace('smtp.', '')
      setSystemConfig({
        ...systemConfig,
        smtp: {
          ...systemConfig.smtp!,
          [smtpKey]: type === 'checkbox' ? checked : (type === 'number' ? parseInt(value) : value)
        }
      })
    } else {
      setSystemConfig({
        ...systemConfig,
        [name]: type === 'number' ? parseInt(value) : value
      })
    }
  }

  const validateAdminUser = (): string[] => {
    const errors: string[] = []
    
    if (!adminUser.username.trim()) {
      errors.push('Username is required')
    }
    
    if (!adminUser.email.trim()) {
      errors.push('Email is required')
    } else if (!/\S+@\S+\.\S+/.test(adminUser.email)) {
      errors.push('Email is invalid')
    }
    
    if (!adminUser.password) {
      errors.push('Password is required')
    } else {
      if (adminUser.password.length < 8) {
        errors.push('Password must be at least 8 characters long')
      }
      if (!/(?=.*[a-z])/.test(adminUser.password)) {
        errors.push('Password must contain at least one lowercase letter')
      }
      if (!/(?=.*[A-Z])/.test(adminUser.password)) {
        errors.push('Password must contain at least one uppercase letter')
      }
      if (!/(?=.*\d)/.test(adminUser.password)) {
        errors.push('Password must contain at least one number')
      }
    }
    
    if (adminUser.password !== adminUser.password_confirm) {
      errors.push('Passwords do not match')
    }
    
    return errors
  }

  const handleInitializeSetup = async () => {
    const userErrors = validateAdminUser()
    if (userErrors.length > 0) {
      setError(userErrors.join('. '))
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch('/api/setup/initialize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Setup-Session': sessionId || '',
        },
        body: JSON.stringify({
          admin_user: {
            username: adminUser.username,
            email: adminUser.email,
            password: adminUser.password
          },
          system_config: {
            ...systemConfig,
            use_case: useCase,
          }
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      if (data.success) {
        // Setup completed successfully
        // Clear setup session
        sessionStorage.removeItem('setup_session_id')
        setSessionId(null)
        
        // If auth_mode is not "free", automatically log in the admin user
        if (systemConfig.auth_mode !== 'free') {
          try {
            await login(adminUser.email, adminUser.password, true) // rememberMe = true
            // Navigate to home page after successful login (only once)
            window.location.href = '/' // Use window.location to avoid React Router loops
          } catch (loginError) {
            // Login failed, but setup was successful - redirect to login page
            console.error('Auto-login after setup failed:', loginError)
            window.location.href = '/login' // Use window.location to avoid React Router loops
          }
        } else {
          // Free mode - no login required, go to home
          window.location.href = '/' // Use window.location to avoid React Router loops
        }
      } else {
        setError('Setup failed. Please try again.')
      }
    } catch (err: any) {
      setError('Setup failed. Please try again.')
      console.error('Setup initialization failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const renderStep0 = () => (
    <div className="setup-step">
      <h3>Step 0: Verify Setup Token</h3>
      <p style={{ marginBottom: '20px', color: '#666' }}>
        Please enter the setup token that was generated when the server started.
        You can find it in the server logs.
      </p>
      <div className="form-group">
        <label>Setup Token</label>
        <input
          type="text"
          value={setupToken}
          onChange={(e) => setSetupToken(e.target.value)}
          placeholder="Enter setup token"
          style={{
            width: '100%',
            padding: '12px',
            fontSize: '16px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            fontFamily: 'monospace'
          }}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              handleVerifyToken()
            }
          }}
        />
      </div>
      <div className="step-actions">
        <button 
          onClick={handleVerifyToken} 
          disabled={loading || !setupToken.trim()}
          style={{ width: '100%' }}
        >
          {loading ? 'Verifying...' : 'Verify Token'}
        </button>
      </div>
    </div>
  )

  const renderStep1 = () => (
    <div className="setup-step">
      <h3>Step 1: Select Deployment Use Case</h3>
      <p style={{ marginBottom: '24px', color: '#666' }}>
        Choose the deployment scenario that best matches your setup. This will configure security settings and rate limits automatically.
      </p>
      
      <div style={{ display: 'grid', gap: '16px', marginBottom: '24px' }}>
        <div
          onClick={() => handleUseCaseSelect('solo')}
          style={{
            padding: '20px',
            border: `2px solid ${useCase === 'solo' ? '#4CAF50' : '#ddd'}`,
            borderRadius: '8px',
            cursor: 'pointer',
            backgroundColor: useCase === 'solo' ? '#f0f9f0' : '#fff',
            transition: 'all 0.2s',
          }}
        >
          <h4 style={{ margin: '0 0 8px 0' }}>Solo</h4>
          <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#666' }}>
            Single user, self-hosted. All features enabled, no restrictions.
          </p>
          <small style={{ color: '#888' }}>Security: Permissive | Auth: Free</small>
        </div>
        
        <div
          onClick={() => handleUseCaseSelect('network_intern')}
          style={{
            padding: '20px',
            border: `2px solid ${useCase === 'network_intern' ? '#4CAF50' : '#ddd'}`,
            borderRadius: '8px',
            cursor: 'pointer',
            backgroundColor: useCase === 'network_intern' ? '#f0f9f0' : '#fff',
            transition: 'all 0.2s',
          }}
        >
          <h4 style={{ margin: '0 0 8px 0' }}>Network Intern</h4>
          <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#666' }}>
            Multiple users, internal network. User authentication required.
          </p>
          <small style={{ color: '#888' }}>Security: Permissive | Auth: Basic/JWT</small>
        </div>
        
        <div
          onClick={() => handleUseCaseSelect('public_web')}
          style={{
            padding: '20px',
            border: `2px solid ${useCase === 'public_web' ? '#4CAF50' : '#ddd'}`,
            borderRadius: '8px',
            cursor: 'pointer',
            backgroundColor: useCase === 'public_web' ? '#f0f9f0' : '#fff',
            transition: 'all 0.2s',
          }}
        >
          <h4 style={{ margin: '0 0 8px 0' }}>Public Web</h4>
          <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#666' }}>
            Public web access, many users. Restricted security, rate limited.
          </p>
          <small style={{ color: '#888' }}>Security: Restricted | Auth: Free</small>
        </div>
        
        <div
          onClick={() => handleUseCaseSelect('enterprise')}
          style={{
            padding: '20px',
            border: `2px solid ${useCase === 'enterprise' ? '#4CAF50' : '#ddd'}`,
            borderRadius: '8px',
            cursor: 'pointer',
            backgroundColor: useCase === 'enterprise' ? '#f0f9f0' : '#fff',
            transition: 'all 0.2s',
          }}
        >
          <h4 style={{ margin: '0 0 8px 0' }}>Enterprise</h4>
          <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#666' }}>
            Enterprise deployment with SSO. Restricted security, JWT authentication.
          </p>
          <small style={{ color: '#888' }}>Security: Restricted | Auth: JWT (SSO)</small>
        </div>
      </div>
      
      <div className="step-actions">
        <button onClick={handleNext} disabled={!useCase}>
          Continue
        </button>
      </div>
    </div>
  )
  
  const renderStep2 = () => (
    <div className="setup-step">
      <h3>Step 2: System Requirements</h3>
      <div className="requirements-list">
        <div className="requirement">
          <span className={`status ${setupStatus?.database_connected ? 'success' : 'error'}`}>
            {setupStatus?.database_connected ? '✓' : '✗'}
          </span>
          <span>Database Connection</span>
        </div>
        <div className="requirement">
          <span className={`status ${setupStatus?.tables_exist ? 'success' : 'pending'}`}>
            {Object.values(setupStatus?.tables_exist || {}).every(Boolean) ? '✓' : '○'}
          </span>
          <span>Database Tables</span>
        </div>
        <div className="requirement">
          <span className={`status ${setupStatus?.admin_exists ? 'success' : 'pending'}`}>
            {setupStatus?.admin_exists ? '✓' : '○'}
          </span>
          <span>Admin User</span>
        </div>
        <div className="requirement">
          <span className={`status ${setupStatus?.system_state_exists ? 'success' : 'pending'}`}>
            {setupStatus?.system_state_exists ? '✓' : '○'}
          </span>
          <span>System Configuration</span>
        </div>
      </div>
      <div className="step-actions">
        <button onClick={handleBack}>Back</button>
        <button onClick={handleNext} disabled={loading || !setupStatus?.database_connected}>
          {loading ? 'Checking...' : 'Continue'}
        </button>
      </div>
    </div>
  )

  const renderStep3 = () => (
    <div className="setup-step">
      <h3>Step 3: Create Admin User</h3>
      <div className="form-group">
        <label>Username</label>
        <input
          type="text"
          name="username"
          value={adminUser.username}
          onChange={handleAdminUserChange}
          placeholder="Enter admin username"
        />
      </div>
      <div className="form-group">
        <label>Email</label>
        <input
          type="email"
          name="email"
          value={adminUser.email}
          onChange={handleAdminUserChange}
          placeholder="Enter admin email"
        />
      </div>
      <div className="form-group">
        <label>Password</label>
        <input
          type="password"
          name="password"
          value={adminUser.password}
          onChange={handleAdminUserChange}
          placeholder="Enter admin password"
        />
        <div className="password-requirements">
          <small>Password must contain:</small>
          <ul>
            <li className={adminUser.password.length >= 8 ? 'valid' : ''}>At least 8 characters</li>
            <li className={/(?=.*[a-z])/.test(adminUser.password) ? 'valid' : ''}>One lowercase letter</li>
            <li className={/(?=.*[A-Z])/.test(adminUser.password) ? 'valid' : ''}>One uppercase letter</li>
            <li className={/(?=.*\d)/.test(adminUser.password) ? 'valid' : ''}>One number</li>
          </ul>
        </div>
      </div>
      <div className="form-group">
        <label>Confirm Password</label>
        <input
          type="password"
          name="password_confirm"
          value={adminUser.password_confirm}
          onChange={handleAdminUserChange}
          placeholder="Confirm admin password"
        />
      </div>
      <div className="step-actions">
        <button onClick={handleBack}>Back</button>
        <button onClick={handleNext} disabled={loading || validateAdminUser().length > 0}>
          Next
        </button>
      </div>
    </div>
  )

  const renderStep4 = () => (
    <div className="setup-step">
      <h3>Step 4: System Configuration</h3>
      <p style={{ marginBottom: '20px', color: '#666', fontSize: '14px' }}>
        Configuration based on your selected use case: <strong>{useCase}</strong>
      </p>
      
      <div className="form-group">
        <label>Authentication Mode</label>
        <select
          name="auth_mode"
          value={systemConfig.auth_mode}
          onChange={handleSystemConfigChange}
          disabled={useCase === 'solo' || useCase === 'public_web'} // Locked for these use cases
        >
          <option value="free">Free (No Authentication)</option>
          <option value="basic">Basic (Username/Password)</option>
          <option value="jwt">JWT (Token-based / SSO)</option>
        </select>
        {useCase === 'network_intern' && (
          <small style={{ color: '#666', display: 'block', marginTop: '4px' }}>
            Can be changed to JWT for SSO integration
          </small>
        )}
      </div>
      <div className="form-group">
        <label>Scanner Timeout (seconds)</label>
        <input
          type="number"
          name="scanner_timeout"
          value={systemConfig.scanner_timeout}
          onChange={handleSystemConfigChange}
          min="60"
          max="7200"
        />
      </div>
      <div className="form-group">
        <label>Max Concurrent Scans</label>
        <input
          type="number"
          name="max_concurrent_scans"
          value={systemConfig.max_concurrent_scans}
          onChange={handleSystemConfigChange}
          min="1"
          max="20"
        />
      </div>
      
      <div style={{ marginTop: '32px', paddingTop: '24px', borderTop: '1px solid #ddd' }}>
        <h4 style={{ marginBottom: '16px' }}>Email Configuration (Optional)</h4>
        <p style={{ fontSize: '14px', color: '#666', marginBottom: '16px' }}>
          Configure SMTP settings to enable password reset emails. This can be configured later in Admin Settings.
        </p>
        
        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              name="smtp.enabled"
              checked={systemConfig.smtp?.enabled || false}
              onChange={handleSystemConfigChange}
              style={{ cursor: 'pointer' }}
            />
            <span>Enable SMTP Email</span>
          </label>
        </div>
        
        {systemConfig.smtp?.enabled && (
          <>
            <div className="form-group">
              <label>SMTP Host</label>
              <input
                type="text"
                name="smtp.host"
                value={systemConfig.smtp.host}
                onChange={handleSystemConfigChange}
                placeholder="smtp.gmail.com"
              />
            </div>
            <div className="form-group">
              <label>SMTP Port</label>
              <input
                type="number"
                name="smtp.port"
                value={systemConfig.smtp.port}
                onChange={handleSystemConfigChange}
                placeholder="587"
                min="1"
                max="65535"
              />
            </div>
            <div className="form-group">
              <label>SMTP Username/Email</label>
              <input
                type="email"
                name="smtp.user"
                value={systemConfig.smtp.user}
                onChange={handleSystemConfigChange}
                placeholder="your@email.com"
              />
            </div>
            <div className="form-group">
              <label>SMTP Password</label>
              <input
                type="password"
                name="smtp.password"
                value={systemConfig.smtp.password}
                onChange={handleSystemConfigChange}
                placeholder="SMTP password or app password"
              />
            </div>
            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="smtp.use_tls"
                  checked={systemConfig.smtp.use_tls}
                  onChange={handleSystemConfigChange}
                  style={{ cursor: 'pointer' }}
                />
                <span>Use TLS</span>
              </label>
            </div>
            <div className="form-group">
              <label>From Email</label>
              <input
                type="email"
                name="smtp.from_email"
                value={systemConfig.smtp.from_email}
                onChange={handleSystemConfigChange}
                placeholder="noreply@simpleseccheck.local"
              />
            </div>
            <div className="form-group">
              <label>From Name</label>
              <input
                type="text"
                name="smtp.from_name"
                value={systemConfig.smtp.from_name}
                onChange={handleSystemConfigChange}
                placeholder="SimpleSecCheck"
              />
            </div>
          </>
        )}
      </div>
      
      <div className="step-actions">
        <button onClick={handleBack}>Back</button>
        <button onClick={handleInitializeSetup} disabled={loading}>
          {loading ? 'Setting up...' : 'Complete Setup'}
        </button>
      </div>
    </div>
  )

  const renderStepContent = () => {
    switch (step) {
      case 0: return renderStep0()
      case 1: return renderStep1()
      case 2: return renderStep2()
      case 3: return renderStep3()
      case 4: return renderStep4()
      default: return renderStep0()
    }
  }

  if (loading && !setupStatus) {
    return (
      <div className="container">
        <div className="card">
          <h2>Setup Wizard</h2>
          <div className="loading">Checking system status...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Setup Wizard</h2>
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        <div className="setup-progress">
          <div className={`progress-step ${step >= 0 ? 'active' : ''}`}>
            <div className="step-number">0</div>
            <div className="step-label">Token</div>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step >= 1 ? 'active' : ''}`}>
            <div className="step-number">1</div>
            <div className="step-label">Requirements</div>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step >= 2 ? 'active' : ''}`}>
            <div className="step-number">2</div>
            <div className="step-label">Admin User</div>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step >= 3 ? 'active' : ''}`}>
            <div className="step-number">3</div>
            <div className="step-label">Configuration</div>
          </div>
        </div>

        {renderStepContent()}
      </div>
    </div>
  )
}