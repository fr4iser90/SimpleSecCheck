import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { apiFetch } from '../utils/apiClient'

export default function AdminPoliciesPage() {
  const { user, isAuthenticated } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [blockedPatterns, setBlockedPatterns] = useState('')
  const [blockedScanTypes, setBlockedScanTypes] = useState('')
  const [requireAuthForGit, setRequireAuthForGit] = useState(false)

  const load = async () => {
    try {
      setLoading(true)
      setError(null)
      const r = await apiFetch('/api/admin/config/scan-enforcement')
      if (!r.ok) throw new Error('Failed to load policies')
      const data = await r.json()
      const pol = data.policies || {}
      const pats = pol.blocked_target_patterns
      setBlockedPatterns(Array.isArray(pats) ? pats.join('\n') : '')
      const types = pol.blocked_scan_types
      setBlockedScanTypes(Array.isArray(types) ? types.join(', ') : '')
      setRequireAuthForGit(Boolean(pol.require_auth_for_git))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Load failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated || !isAdmin) return
    void load()
  }, [isAuthenticated, isAdmin])

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      const blocked_target_patterns = blockedPatterns
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean)
      const blocked_scan_types = blockedScanTypes
        .split(/[,;\s]+/)
        .map((s) => s.trim().toLowerCase())
        .filter(Boolean)
      const r = await apiFetch('/api/admin/config/scan-enforcement', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          policies: {
            blocked_target_patterns,
            blocked_scan_types,
            require_auth_for_git: requireAuthForGit,
          },
        }),
      })
      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail || 'Save failed')
      }
      setSuccess('Policies saved. New scan submissions are checked immediately.')
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (!isAdmin) {
    return (
      <div className="admin-settings-page">
        <div className="admin-settings-container">
          <h2>Access Denied</h2>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-settings-page">
      <div className="admin-settings-container">
        <p style={{ marginBottom: '1rem' }}>
          <Link to="/admin">← Admin</Link>
        </p>
        <h2>Security policies</h2>
        <p className="section-description">
          Rules enforced on <strong>every new scan</strong> (403 if blocked). Rate limits and max scan duration:{' '}
          <Link to="/admin/execution">Execution</Link>.
        </p>

        {loading ? (
          <p style={{ marginTop: '1rem' }}>Loading…</p>
        ) : (
          <form
            onSubmit={save}
            className="settings-form"
            style={{
              marginTop: '1.5rem',
              padding: '1.25rem',
              border: '1px solid var(--glass-border-main)',
              borderRadius: 12,
              background: 'var(--glass-bg-main)',
            }}
          >
            {error && (
              <div className="error-message" role="alert" style={{ marginBottom: '1rem' }}>
                {error}
              </div>
            )}
            <div className="form-group">
              <label>Blocked target patterns (one per line)</label>
              <textarea
                rows={6}
                value={blockedPatterns}
                onChange={(e) => setBlockedPatterns(e.target.value)}
                placeholder={`file://*\n*.corp.internal\nregex:https?://10\\\\.`}
                style={{ width: '100%', fontFamily: 'monospace', fontSize: '0.9rem' }}
              />
              <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                Glob match against target URL, or prefix with <code>regex:</code> for a Python regex.
              </small>
            </div>
            <div className="form-group">
              <label>Blocked scan types</label>
              <input
                type="text"
                value={blockedScanTypes}
                onChange={(e) => setBlockedScanTypes(e.target.value)}
                placeholder="code, container, website, network"
                style={{ width: '100%' }}
              />
              <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                Comma-separated: <code>code</code>, <code>container</code>, <code>website</code>,{' '}
                <code>network</code>.
              </small>
            </div>
            <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                id="req_git"
                type="checkbox"
                checked={requireAuthForGit}
                onChange={(e) => setRequireAuthForGit(e.target.checked)}
              />
              <label htmlFor="req_git" style={{ margin: 0 }}>
                Require login for Git repository scans (block guest git scans)
              </label>
            </div>
            {success && (
              <div className="success-message" role="status" style={{ marginBottom: '1rem' }}>
                {success}
              </div>
            )}
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save policies'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
