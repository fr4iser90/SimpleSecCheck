import React, { useState, useEffect } from 'react';
import '../Setup.css';

interface SystemCheck {
  name: string;
  status: 'loading' | 'success' | 'error';
  message: string;
}

interface AdminFormData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const Setup: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [checkingSystem, setCheckingSystem] = useState(false);
  const [systemReady, setSystemReady] = useState(false);
  
  const [systemChecks, setSystemChecks] = useState<SystemCheck[]>([
    { name: 'Database Connection', status: 'loading', message: '' },
    { name: 'Redis Connection', status: 'loading', message: '' },
    { name: 'Docker Access', status: 'loading', message: '' },
    { name: 'Disk Space', status: 'loading', message: '' },
    { name: 'Memory', status: 'loading', message: '' }
  ]);

  const [adminForm, setAdminForm] = useState<AdminFormData>({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  });

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Check if setup is already completed
  useEffect(() => {
    checkSetupStatus();
  }, []);

  const checkSetupStatus = async () => {
    try {
      const response = await fetch('/api/setup/status');
      const data = await response.json();
      
      if (!data.setup_required) {
        // Setup already completed, redirect to main app
        window.location.href = '/';
      }
    } catch (err) {
      console.error('Failed to check setup status:', err);
    }
  };

  const checkSystemRequirements = async () => {
    setCheckingSystem(true);
    setError(null);
    
    try {
      const response = await fetch('/api/setup/health');
      const data = await response.json();
      
      // Update system checks based on response
      const updatedChecks = systemChecks.map(check => {
        const apiCheck = data[check.name.toLowerCase().replace(' ', '_')];
        if (apiCheck) {
          const newStatus: 'success' | 'error' = apiCheck.status === 'connected' ? 'success' : 'error';
          return {
            ...check,
            status: newStatus,
            message: apiCheck.status === 'error' ? apiCheck.message || 'Connection failed' : ''
          };
        }
        return { ...check, status: 'error' as const, message: 'Check failed' };
      });
      
      setSystemChecks(updatedChecks);
      setSystemReady(updatedChecks.every(check => check.status === 'success'));
    } catch (err) {
      setError('Failed to check system requirements');
      setSystemChecks(systemChecks.map(check => ({ ...check, status: 'error', message: 'Check failed' })));
    } finally {
      setCheckingSystem(false);
    }
  };

  const nextStep = () => {
    if (currentStep < 2) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setAdminForm(prev => ({ ...prev, [name]: value }));
  };

  const getPasswordStrength = () => {
    const password = adminForm.password;
    let score = 0;
    
    if (password.length >= 8) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;
    
    return score;
  };

  const getPasswordStrengthText = () => {
    const score = getPasswordStrength();
    if (score <= 2) return 'Weak';
    if (score <= 3) return 'Medium';
    return 'Strong';
  };

  const getPasswordStrengthClass = () => {
    const score = getPasswordStrength();
    if (score <= 2) return 'weak';
    if (score <= 3) return 'medium';
    return 'strong';
  };

  const passwordMismatch = adminForm.password && adminForm.password !== adminForm.confirmPassword;
  const canCreateAdmin = 
    adminForm.name &&
    adminForm.email &&
    adminForm.password &&
    !passwordMismatch &&
    getPasswordStrength() >= 3;

  const createAdminUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/setup/initialize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          admin_user: {
            name: adminForm.name,
            email: adminForm.email,
            password: adminForm.password
          }
        })
      });

      const data = await response.json();

      if (response.ok) {
        setCurrentStep(2);
      } else {
        setError(data.message || 'Failed to create admin user');
      }
    } catch (err) {
      setError('Failed to create admin user');
    } finally {
      setLoading(false);
    }
  };

  const finishSetup = () => {
    // Redirect to main application
    window.location.href = '/';
  };

  const steps = [
    { title: 'System Check', description: 'Verify system requirements are met' },
    { title: 'Admin Setup', description: 'Create your admin account' },
    { title: 'Complete', description: 'Setup finished successfully' }
  ];

  return (
    <div className="setup-container">
      <div className="setup-card">
        <div className="setup-header">
          <h1>SimpleSecCheck Setup</h1>
          <p>Complete the initial setup to get started</p>
        </div>

        {/* Setup Steps */}
        <div className="setup-steps">
          {steps.map((step, index) => (
            <div 
              key={index} 
              className={`step ${currentStep === index ? 'active' : ''} ${currentStep > index ? 'completed' : ''}`}
            >
              <div className="step-number">{index + 1}</div>
              <div className="step-content">
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {/* Setup Content */}
        <div className="setup-content">
          {/* Step 1: System Check */}
          {currentStep === 0 && (
            <div className="setup-step">
              <h2>System Requirements Check</h2>
              <div className="system-check">
                {systemChecks.map((check, index) => (
                  <div key={index} className="check-item">
                    <div className="check-icon">
                      {check.status === 'loading' && <span className="loading">⟳</span>}
                      {check.status === 'success' && <span className="success">✓</span>}
                      {check.status === 'error' && <span className="error">✗</span>}
                    </div>
                    <div className="check-info">
                      <strong>{check.name}</strong>
                      <span className="check-status">{check.status}</span>
                      {check.message && <span className="check-message">{check.message}</span>}
                    </div>
                  </div>
                ))}
              </div>
              <div className="setup-actions">
                <button 
                  onClick={checkSystemRequirements} 
                  disabled={checkingSystem}
                  className="btn-primary"
                >
                  {checkingSystem ? 'Checking...' : 'Check Requirements'}
                </button>
                {systemReady && (
                  <button 
                    onClick={nextStep} 
                    className="btn-primary"
                  >
                    Continue
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Step 2: Admin User Setup */}
          {currentStep === 1 && (
            <div className="setup-step">
              <h2>Admin User Setup</h2>
              <form onSubmit={createAdminUser} className="setup-form">
                <div className="form-group">
                  <label htmlFor="name">Full Name</label>
                  <input 
                    type="text" 
                    id="name" 
                    name="name"
                    value={adminForm.name}
                    onChange={handleInputChange}
                    required
                    placeholder="Enter your full name"
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="email">Email Address</label>
                  <input 
                    type="email" 
                    id="email" 
                    name="email"
                    value={adminForm.email}
                    onChange={handleInputChange}
                    required
                    placeholder="admin@example.com"
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="password">Password</label>
                  <input 
                    type="password" 
                    id="password" 
                    name="password"
                    value={adminForm.password}
                    onChange={handleInputChange}
                    required
                    placeholder="Enter a strong password"
                    minLength={8}
                  />
                  {adminForm.password && (
                    <div className="password-strength">
                      <div className={`strength-bar ${getPasswordStrengthClass()}`}></div>
                      <span className="strength-text">{getPasswordStrengthText()}</span>
                    </div>
                  )}
                </div>
                
                <div className="form-group">
                  <label htmlFor="confirmPassword">Confirm Password</label>
                  <input 
                    type="password" 
                    id="confirmPassword" 
                    name="confirmPassword"
                    value={adminForm.confirmPassword}
                    onChange={handleInputChange}
                    required
                    placeholder="Confirm your password"
                  />
                  {passwordMismatch && (
                    <div className="error-message">
                      Passwords do not match
                    </div>
                  )}
                </div>

                <div className="setup-actions">
                  <button type="button" onClick={prevStep} className="btn-secondary">Back</button>
                  <button 
                    type="submit" 
                    disabled={!canCreateAdmin || loading}
                    className="btn-primary"
                  >
                    {loading ? 'Creating...' : 'Create Admin User'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Step 3: Completion */}
          {currentStep === 2 && (
            <div className="setup-step">
              <h2>Setup Complete!</h2>
              <div className="completion-message">
                <div className="success-icon">✓</div>
                <p>Your SimpleSecCheck system has been successfully set up.</p>
                <p>Admin user created: <strong>{adminForm.email}</strong></p>
              </div>
              <div className="setup-actions">
                <button onClick={finishSetup} className="btn-primary">Go to Dashboard</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Setup;