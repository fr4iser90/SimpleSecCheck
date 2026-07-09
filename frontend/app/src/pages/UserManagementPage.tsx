import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import AdminPageShell from '../components/AdminPageShell'
import AdminPanel from '../components/AdminPanel'
import { useToast } from '../context/ToastContext'
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
  const toast = useToast()
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
        toast.success('User created')
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Failed to create user')
      }
    } catch (error) {
      console.error('Failed to create user:', error)
      toast.error('Failed to create user')
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
        toast.success('User updated')
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Failed to update user')
      }
    } catch (error) {
      console.error('Failed to update user:', error)
      toast.error('Failed to update user')
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
        toast.success('User deleted')
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Failed to delete user')
      }
    } catch (error) {
      console.error('Failed to delete user:', error)
      toast.error('Failed to delete user')
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
        toast.success('User activated')
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Failed to activate user')
      }
    } catch (error) {
      console.error('Failed to activate user:', error)
      toast.error('Failed to activate user')
    }
  }

  return (
    <AdminPageShell
      title="User Management"
      subtitle="Create accounts, assign roles, and approve pending registrations."
      calloutTitle="Quick reference"
      callout={
        <dl className="page-kv-list">
          <div>
            <dt>Roles</dt>
            <dd>Admin users can access all settings; standard users run scans within policy limits.</dd>
          </div>
          <div>
            <dt>Pending</dt>
            <dd>Users awaiting approval appear when registration requires admin sign-off.</dd>
          </div>
          <div>
            <dt>Auth</dt>
            <dd>Self-registration and access mode: <Link to="/admin/auth">Auth settings</Link>.</dd>
          </div>
        </dl>
      }
      loading={loading}
      actions={
        <div className="admin-page-actions">
          <div className="segmented-tabs">
            {(['all', 'active', 'pending'] as const).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`segmented-tab${filter === f ? ' segmented-tab--active' : ''}`}
              >
                {f === 'all' ? 'All' : f === 'pending' ? 'Pending approval' : 'Active'}
              </button>
            ))}
          </div>
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            + Create User
          </button>
        </div>
      }
    >
      <AdminPanel flush>
        <div className="desktop-only-table data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Username</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.email}</td>
                  <td>{user.username}</td>
                  <td>
                    <span className={`role-badge role-badge--${user.role === 'admin' ? 'admin' : 'user'}`}>
                      {user.role}
                    </span>
                  </td>
                  <td>
                    {user.is_active ? (
                      <span className="status-pill status-pill--active">Active</span>
                    ) : (
                      <span className="status-pill status-pill--pending">Pending approval</span>
                    )}
                  </td>
                  <td>{new Date(user.created_at).toLocaleDateString()}</td>
                  <td>
                    <div className="admin-page-actions">
                      {!user.is_active && (
                        <button type="button" className="btn-secondary" onClick={() => handleAccept(user)}>
                          Accept
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => {
                          setEditingUser(user)
                          setFormData({ email: user.email, username: user.username, password: '', role: user.role })
                        }}
                      >
                        Edit
                      </button>
                      <button type="button" className="btn-danger" onClick={() => handleDelete(user.id)}>
                        {user.is_active ? 'Delete' : 'Reject'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mobile-card-list" aria-label="Users (mobile)">
          {users.map((user) => (
            <article key={user.id} className="mobile-data-card">
              <h3 className="mobile-data-card__title">{user.email}</h3>
              <p className="mobile-data-card__subtitle">@{user.username}</p>
              <div className="mobile-data-card__grid">
                <div className="mobile-data-card__row">
                  <span className="mobile-data-card__label">Role</span>
                  <span className={`role-badge role-badge--${user.role === 'admin' ? 'admin' : 'user'}`}>
                    {user.role}
                  </span>
                </div>
                <div className="mobile-data-card__row">
                  <span className="mobile-data-card__label">Status</span>
                  {user.is_active ? (
                    <span className="status-pill status-pill--active">Active</span>
                  ) : (
                    <span className="status-pill status-pill--pending">Pending approval</span>
                  )}
                </div>
                <div className="mobile-data-card__row">
                  <span className="mobile-data-card__label">Created</span>
                  <span className="mobile-data-card__value">{new Date(user.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="mobile-data-card__actions">
                {!user.is_active && (
                  <button type="button" className="btn-secondary" onClick={() => handleAccept(user)}>
                    Accept
                  </button>
                )}
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setEditingUser(user)
                    setFormData({ email: user.email, username: user.username, password: '', role: user.role })
                  }}
                >
                  Edit
                </button>
                <button type="button" className="btn-danger" onClick={() => handleDelete(user.id)}>
                  {user.is_active ? 'Delete' : 'Reject'}
                </button>
              </div>
            </article>
          ))}
        </div>
      </AdminPanel>

      {showCreateModal && (
        <div className="ui-modal-overlay">
          <div className="ui-modal">
            <h2 className="ui-modal__title">Create User</h2>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  required
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="ui-modal__actions">
                <button type="button" className="btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editingUser && (
        <div className="ui-modal-overlay">
          <div className="ui-modal">
            <h2 className="ui-modal__title">Edit User</h2>
            <form onSubmit={handleUpdate}>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="ui-modal__actions">
                <button type="button" className="btn-secondary" onClick={() => setEditingUser(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Update
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AdminPageShell>
  )
}
