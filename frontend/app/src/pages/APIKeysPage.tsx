import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'

interface APIKey {
  id: string
  name: string
  key_prefix: string
  created_at: string
  last_used_at: string | null
  expires_at: string | null
  is_active: boolean
}

export default function APIKeysPage() {
  const [keys, setKeys] = useState<APIKey[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newKey, setNewKey] = useState<{ name: string, expires_in_days: string } | null>(null)
  const [createdKey, setCreatedKey] = useState<{ api_key: string, name: string } | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const loadKeys = async () => {
    setLoading(true)
    try {
      const response = await apiFetch('/api/user/api-keys')
      if (response.ok) {
        const data = await response.json()
        setKeys(data)
      }
    } catch (error) {
      console.error('Failed to load API keys:', error)
      setMessage({ type: 'error', text: 'Failed to load API keys' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadKeys()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKey) return

    try {
      const response = await apiFetch('/api/user/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newKey.name,
          expires_in_days: newKey.expires_in_days ? parseInt(newKey.expires_in_days) : null
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setCreatedKey({ api_key: data.api_key, name: data.name })
        setShowCreateModal(false)
        setNewKey(null)
        loadKeys()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to create API key' })
      }
    } catch (error) {
      console.error('Failed to create API key:', error)
      setMessage({ type: 'error', text: 'Failed to create API key' })
    }
  }

  const handleRevoke = async (keyId: string, keyName: string) => {
    if (!confirm(`Are you sure you want to revoke API key "${keyName}"? This action cannot be undone.`)) {
      return
    }

    try {
      const response = await apiFetch(`/api/user/api-keys/${keyId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        setMessage({ type: 'success', text: 'API key revoked successfully' })
        setTimeout(() => setMessage(null), 3000)
        loadKeys()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to revoke API key' })
      }
    } catch (error) {
      console.error('Failed to revoke API key:', error)
      setMessage({ type: 'error', text: 'Failed to revoke API key' })
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setMessage({ type: 'success', text: 'Copied to clipboard!' })
    setTimeout(() => setMessage(null), 2000)
  }

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>API Keys</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Manage your API keys for programmatic access
          </p>
        </div>
        <button className="primary" onClick={() => setShowCreateModal(true)}>
          + Create API Key
        </button>
      </div>

      {message && (
        <div style={{
          padding: '1rem',
          marginBottom: '1.5rem',
          borderRadius: '8px',
          background: message.type === 'success' ? 'rgba(40, 167, 69, 0.2)' : 'rgba(220, 53, 69, 0.2)',
          border: `1px solid ${message.type === 'success' ? 'var(--color-pass)' : 'var(--color-critical)'}`,
          color: message.type === 'success' ? 'var(--color-pass)' : 'var(--color-critical)'
        }}>
          {message.text}
        </div>
      )}

      {/* Show created key (only once) */}
      {createdKey && (
        <div style={{
          padding: '1.5rem',
          marginBottom: '1.5rem',
          borderRadius: '8px',
          background: 'rgba(40, 167, 69, 0.1)',
          border: '2px solid var(--color-pass)'
        }}>
          <h3 style={{ marginTop: 0, color: 'var(--color-pass)' }}>API Key Created!</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            <strong>Important:</strong> This is the only time you'll see this API key. Make sure to copy it now.
          </p>
          <div style={{
            display: 'flex',
            gap: '0.5rem',
            alignItems: 'center',
            marginBottom: '1rem',
            padding: '1rem',
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: '8px',
            fontFamily: 'monospace'
          }}>
            <code style={{ flex: 1, wordBreak: 'break-all' }}>{createdKey.api_key}</code>
            <button onClick={() => copyToClipboard(createdKey.api_key)}>
              Copy
            </button>
          </div>
          <button onClick={() => setCreatedKey(null)}>Close</button>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading...</div>
      ) : (
        <div style={{
          background: 'var(--glass-bg-main)',
          borderRadius: '8px',
          overflow: 'hidden',
          border: '1px solid var(--glass-border-main)'
        }}>
          {keys.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              No API keys found. Create your first API key to get started.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'rgba(255, 255, 255, 0.05)' }}>
                  <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>Name</th>
                  <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>Key Prefix</th>
                  <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>Created</th>
                  <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>Last Used</th>
                  <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>Expires</th>
                  <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((key) => (
                  <tr key={key.id} style={{ borderBottom: '1px solid var(--glass-border-main)' }}>
                    <td style={{ padding: '1rem', fontSize: '0.9rem' }}>{key.name}</td>
                    <td style={{ padding: '1rem', fontSize: '0.9rem', fontFamily: 'monospace' }}>
                      {key.key_prefix}...
                    </td>
                    <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                      {new Date(key.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                      {key.last_used_at ? new Date(key.last_used_at).toLocaleString() : 'Never'}
                    </td>
                    <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                      {key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never'}
                    </td>
                    <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                      <button
                        onClick={() => handleRevoke(key.id, key.name)}
                        style={{ fontSize: '0.85rem', padding: '0.25rem 0.5rem', background: 'var(--color-critical)' }}
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'var(--glass-bg-main)',
            padding: '2rem',
            borderRadius: '8px',
            width: '90%',
            maxWidth: '500px',
            border: '1px solid var(--glass-border-main)'
          }}>
            <h2 style={{ marginTop: 0 }}>Create API Key</h2>
            <form onSubmit={handleCreate}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Name</label>
                <input
                  type="text"
                  required
                  placeholder="My API Key"
                  value={newKey?.name || ''}
                  onChange={(e) => setNewKey({ ...(newKey || { name: '', expires_in_days: '' }), name: e.target.value })}
                  style={{ width: '100%' }}
                />
                <small style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  A descriptive name for this API key
                </small>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Expires In (Days)</label>
                <input
                  type="number"
                  min="1"
                  placeholder="Leave empty for never expires"
                  value={newKey?.expires_in_days || ''}
                  onChange={(e) => setNewKey({ ...(newKey || { name: '', expires_in_days: '' }), expires_in_days: e.target.value })}
                  style={{ width: '100%' }}
                />
                <small style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  Leave empty if the key should never expire
                </small>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button type="button" onClick={() => {
                  setShowCreateModal(false)
                  setNewKey(null)
                }}>
                  Cancel
                </button>
                <button type="submit" className="primary">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
