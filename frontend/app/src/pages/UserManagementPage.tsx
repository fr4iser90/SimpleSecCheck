import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'

interface User {
  id: string
  email: string
  username: string
  role: string
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login: string | null
}

type ListFilter = 'all' | 'active' | 'pending'

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<ListFilter>('all')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    role: 'user'
  })

  const loadUsers = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filter === 'pending') params.set('status', 'pending')
      if (filter === 'active') params.set('status', 'active')
      const url = params.toString() ? `/api/admin/users?${params}` : '/api/admin/users'
      const response = await apiFetch(url)
      if (response.ok) {
        const data = await response.json()
        setUsers(data)
      }
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [filter])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await apiFetch('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      if (response.ok) {
        setShowCreateModal(false)
        setFormData({ email: '', username: '', password: '', role: 'user' })
        loadUsers()
      } else {
        const error = await response.json()
        alert(error.detail || 'Failed to create user')
      }
    } catch (error) {
      console.error('Failed to create user:', error)
      alert('Failed to create user')
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingUser) return
    try {
      const response = await apiFetch(`/api/admin/users/${editingUser.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email || undefined,
          username: formData.username || undefined,
          role: formData.role || undefined
        })
      })
      if (response.ok) {
        setEditingUser(null)
        setFormData({ email: '', username: '', password: '', role: 'user' })
        loadUsers()
      } else {
        const error = await response.json()
        alert(error.detail || 'Failed to update user')
      }
    } catch (error) {
      console.error('Failed to update user:', error)
      alert('Failed to update user')
    }
  }

  const handleDelete = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user?')) return
    try {
      const response = await apiFetch(`/api/admin/users/${userId}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        loadUsers()
      } else {
        const error = await response.json()
        alert(error.detail || 'Failed to delete user')
      }
    } catch (error) {
      console.error('Failed to delete user:', error)
      alert('Failed to delete user')
    }
  }

  const handleAccept = async (user: User) => {
    try {
      const response = await apiFetch(`/api/admin/users/${user.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: true })
      })
      if (response.ok) {
        loadUsers()
      } else {
        const error = await response.json()
        alert(error.detail || 'Failed to activate user')
      }
    } catch (error) {
      console.error('Failed to activate user:', error)
      alert('Failed to activate user')
    }
  }

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>User Management</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Manage user accounts, roles, and permissions
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ marginRight: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Show:</span>
          {(['all', 'active', 'pending'] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={filter === f ? 'primary' : ''}
              style={{
                padding: '0.35rem 0.75rem',
                borderRadius: '6px',
                border: filter === f ? 'none' : '1px solid var(--glass-border-main)',
                background: filter === f ? undefined : 'transparent',
                cursor: 'pointer',
                fontSize: '0.9rem'
              }}
            >
              {f === 'all' ? 'All' : f === 'pending' ? 'Pending approval' : 'Active'}
            </button>
          ))}
        </div>
        <button className="primary" onClick={() => setShowCreateModal(true)}>
          + Create User
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading...</div>
      ) : (
        <div style={{
          background: 'var(--glass-bg-main)',
          borderRadius: '8px',
          overflow: 'hidden',
          border: '1px solid var(--glass-border-main)'
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr className="table-head-row">
                <th className="table-cell-head">Email</th>
                <th className="table-cell-head">Username</th>
                <th className="table-cell-head">Role</th>
                <th className="table-cell-head">Status</th>
                <th className="table-cell-head">Created</th>
                <th className="table-cell-head">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="table-row-divider">
                  <td className="table-cell">{user.email}</td>
                  <td className="table-cell">{user.username}</td>
                  <td className="table-cell">
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      background: user.role === 'admin' ? 'rgba(220, 53, 69, 0.2)' : 'rgba(40, 167, 69, 0.2)',
                      color: user.role === 'admin' ? 'var(--color-critical)' : 'var(--color-pass)'
                    }}>
                      {user.role}
                    </span>
                  </td>
                  <td className="table-cell">
                    {user.is_active ? 'Active' : <span style={{ color: 'var(--color-medium)' }}>Pending approval</span>}
                  </td>
                  <td className="table-cell">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="table-cell">
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {!user.is_active && (
                        <button
                          onClick={() => handleAccept(user)}
                          style={{ fontSize: '0.85rem', padding: '0.25rem 0.5rem', background: 'var(--color-pass)' }}
                        >
                          Accept
                        </button>
                      )}
                      <button
                        onClick={() => {
                          setEditingUser(user)
                          setFormData({ email: user.email, username: user.username, password: '', role: user.role })
                        }}
                        style={{ fontSize: '0.85rem', padding: '0.25rem 0.5rem' }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(user.id)}
                        style={{ fontSize: '0.85rem', padding: '0.25rem 0.5rem', background: 'var(--color-critical)' }}
                      >
                        {user.is_active ? 'Delete' : 'Reject'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
          background: 'var(--modal-overlay-bg)',
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
            <h2 style={{ marginTop: 0 }}>Create User</h2>
            <form onSubmit={handleCreate}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Email</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Username</label>
                <input
                  type="text"
                  required
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Role</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  style={{ width: '100%' }}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button type="button" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="primary">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingUser && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'var(--modal-overlay-bg)',
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
            <h2 style={{ marginTop: 0 }}>Edit User</h2>
            <form onSubmit={handleUpdate}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Username</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Role</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  style={{ width: '100%' }}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button type="button" onClick={() => setEditingUser(null)}>Cancel</button>
                <button type="submit" className="primary">Update</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
