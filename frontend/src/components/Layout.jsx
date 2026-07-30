import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark small">SS</div>
          <span>ScholarShield</span>
        </div>
        <nav>
          <div className="nav-group-label">Tools</div>
          <NavLink to="/" end>All tools</NavLink>
          <NavLink to="/tools/ai-detector">AI Detector</NavLink>
          <NavLink to="/tools/humanizer">Humanizer</NavLink>
          <NavLink to="/tools/plagiarism">Plagiarism Checker</NavLink>
          <NavLink to="/tools/grammar">Grammar &amp; Citations</NavLink>
          <div className="nav-group-label">Documents</div>
          <NavLink to="/documents">Document Scan</NavLink>
          <div className="nav-group-label">Account</div>
          <NavLink to="/security">Security</NavLink>
          {user?.role === 'Admin' && <NavLink to="/admin">Admin analytics</NavLink>}
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="avatar">{user?.full_name?.[0]?.toUpperCase() || '?'}</div>
            <div>
              <div className="user-name">{user?.full_name}</div>
              <div className="user-role">{user?.role}</div>
            </div>
          </div>
          <button
            className="btn-ghost"
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  )
}
