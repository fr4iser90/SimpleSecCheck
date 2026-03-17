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
  const [autoLogin, setAutoLogin] = useState(true) // Default: auto-login enabled
  
  const [useCase, setUseCase] = useState<string>('')
  const [useCases, setUseCases] = useState<Record<string, any>>({})
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
    loadUseCases()
  }, [])

  const loadUseCases = async () => {
    try {
      const response = await fetch('/api/setup/use-cases')
      if (response.ok) {
        const data = await response.json()
        setUseCases(data)
      }
    } catch (err) {
      console.error('Failed to load use cases:', err)
    }
  }

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
    if (step < 3) {
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
    if (step > 0) {
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
        
        // Auto-login if enabled (default for all modes, user can disable)
        if (autoLogin) {
          try {
            await login(adminUser.email, adminUser.password, true)
            // Brief delay so browser commits refresh_token cookie before full reload
            await new Promise((r) => setTimeout(r, 150))
            window.location.href = '/'
          } catch (loginError) {
            console.error('Auto-login after setup failed:', loginError)
            if (systemConfig.auth_mode !== 'free') {
              window.location.href = '/login'
            } else {
              window.location.href = '/'
            }
          }
        } else {
          if (systemConfig.auth_mode !== 'free') {
            window.location.href = '/login'
          } else {
            window.location.href = '/'
          }
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
      <p>
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
          style={{ fontFamily: 'monospace' }}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              handleVerifyToken()
            }
          }}
        />
      </div>
      <div className="step-actions">
        <button 
          className="primary"
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
      <p>
        Choose the deployment scenario that best matches your setup. This will configure security settings and rate limits automatically.
      </p>
      
      {/* Database Connection Check */}
      {setupStatus && !setupStatus.database_connected && (
        <div className="form-info-box error" style={{ marginBottom: '1.5rem' }}>
          <strong>⚠️ Database Connection Required</strong>
          <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>
            Please ensure the database is running and accessible before continuing.
          </p>
        </div>
      )}
      
      {/* Security Mode Explanation (from backend) */}
      <div style={{ display: 'grid', gap: '1rem', marginBottom: '1.5rem' }}>
        {Object.values(useCases).length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            Loading use cases...
          </div>
        ) : (
          Object.values(useCases).map((uc: any) => {
            const authModeLabel = uc.auth_mode === 'free' ? 'Free' : uc.auth_mode === 'basic' ? 'Basic/JWT' : 'JWT (SSO)'
            const featuresText = uc.features.map((f: any) => {
              const prefix = f.type === 'allowed' ? '✓' : f.type === 'info' ? 'ℹ' : '✗'
              return `${prefix} ${f.text}`
            }).join(' | ')
            
            return (
              <div
                key={uc.id}
                className={`use-case-card ${useCase === uc.id ? 'selected' : ''}`}
                onClick={() => handleUseCaseSelect(uc.id)}
              >
                <h4>{uc.name}</h4>
                <p>{uc.description}</p>
                <small>Auth: {authModeLabel}</small>
                <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {featuresText}
                </div>
              </div>
            )
          })
        )}
      </div>
      
      <div className="step-actions">
        <button className="primary" onClick={handleNext} disabled={!useCase || (setupStatus?.database_connected === false)}>
          Continue
        </button>
      </div>
    </div>
  )

  const renderStep2 = () => (
    <div className="setup-step">
      <h3>Step 2: Create Admin User</h3>
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
      <div style={{ 
        marginTop: '1.5rem', 
        padding: '1rem', 
        backgroundColor: 'var(--glass-bg-light)', 
        borderRadius: '8px',
        border: '1px solid var(--glass-border-dark)'
      }}>
        <label style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.75rem', 
          cursor: 'pointer',
          fontSize: '0.9rem'
        }}>
          <input
            type="checkbox"
            checked={autoLogin}
            onChange={(e) => setAutoLogin(e.target.checked)}
            style={{ cursor: 'pointer', width: '1.2rem', height: '1.2rem' }}
          />
          <span>
            <strong>Auto-Login nach Setup</strong>
            <span style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
              Automatisch mit den Admin-Daten einloggen, damit du sofort die Admin- und User-Menüs nutzen kannst.
            </span>
          </span>
        </label>
      </div>
      <div className="step-actions">
        <button onClick={handleBack}>Back</button>
        <button className="primary" onClick={handleNext} disabled={loading || validateAdminUser().length > 0}>
          Next
        </button>
      </div>
    </div>
  )

  const renderStep3 = () => (
    <div className="setup-step">
      <h3>Step 3: System Configuration</h3>
      <p>
        Configuration based on your selected use case: <strong>{useCases[useCase]?.name || useCase}</strong>
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
          <small className="form-help-text info" style={{ display: 'block', marginTop: '0.25rem' }}>
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
      
      <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid var(--glass-border-dark)' }}>
        <h4>Email Configuration (Optional)</h4>
        <p style={{ marginBottom: '1rem' }}>
          Configure SMTP settings to enable password reset emails. This can be configured later in Admin Settings.
        </p>
        
        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
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
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
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
      
      {/* Configuration Summary */}
      <div style={{ 
        marginTop: '2rem', 
        paddingTop: '1.5rem', 
        borderTop: '1px solid var(--glass-border-dark)',
        backgroundColor: 'var(--glass-bg-light)',
        padding: '1.5rem',
        borderRadius: '8px'
      }}>
        <h4 style={{ marginTop: 0, marginBottom: '1rem' }}>Configuration Summary</h4>
        <div style={{ display: 'grid', gap: '0.75rem', fontSize: '0.9rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Use Case:</span>
            <strong>{useCases[useCase]?.name || useCase}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Auth Mode:</span>
            <strong>
              {systemConfig.auth_mode === 'free' ? 'Free (No Authentication)' : 
               systemConfig.auth_mode === 'basic' ? 'Basic (Username/Password)' : 
               'JWT (Token-based / SSO)'}
            </strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Allowed Features:</span>
            <strong style={{ textAlign: 'right', maxWidth: '60%' }}>
              {useCases[useCase]?.features?.map((f: any) => {
                const prefix = f.type === 'allowed' ? '✓' : f.type === 'info' ? 'ℹ' : '✗'
                return `${prefix} ${f.text}`
              }).join(' | ') || 'N/A'}
            </strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Scanner Timeout:</span>
            <strong>{systemConfig.scanner_timeout}s</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Max Concurrent Scans:</span>
            <strong>{systemConfig.max_concurrent_scans}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-secondary)' }}>SMTP Email:</span>
            <strong>{systemConfig.smtp?.enabled ? 'Enabled' : 'Disabled'}</strong>
          </div>
        </div>
      </div>
      
      <div className="step-actions">
        <button onClick={handleBack}>Back</button>
        <button className="primary" onClick={handleInitializeSetup} disabled={loading}>
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
          <div className="form-info-box error">
            {error}
          </div>
        )}
        
        <div className="setup-progress">
          <div className={`progress-step ${step > 0 ? 'completed' : step === 0 ? 'active' : ''}`}>
            <div className="step-number">{step > 0 ? '✓' : '0'}</div>
            <div className="step-label">Token</div>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step > 1 ? 'completed' : step === 1 ? 'active' : ''}`}>
            <div className="step-number">{step > 1 ? '✓' : '1'}</div>
            <div className="step-label">Use Case</div>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step > 2 ? 'completed' : step === 2 ? 'active' : ''}`}>
            <div className="step-number">{step > 2 ? '✓' : '2'}</div>
            <div className="step-label">Admin User</div>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step > 3 ? 'completed' : step === 3 ? 'active' : ''}`}>
            <div className="step-number">{step > 3 ? '✓' : '3'}</div>
            <div className="step-label">Configuration</div>
          </div>
        </div>

        {renderStepContent()}
      </div>
    </div>
  )
}