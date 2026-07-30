import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const [mode, setMode] = useState('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [mfaRequired, setMfaRequired] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(email, password, mfaRequired ? totpCode : undefined)
      } else {
        await register(fullName, email, password)
      }
      navigate('/')
    } catch (err) {
      const detail = err.response?.data?.detail
      if (detail === 'MFA_REQUIRED') {
        setMfaRequired(true)
        setError('This account has MFA enabled — enter the 6-digit code from your authenticator app.')
      } else {
        setError(detail || 'Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-brand">
        <div className="brand-mark">SS</div>
        <h1>ScholarShield</h1>
        <p>AI-powered document intelligence &amp; cybersecurity platform</p>
        <ul className="brand-points">
          <li>Multi-model AI-detection consensus</li>
          <li>Hybrid structural + semantic plagiarism matching</li>
          <li>Real ClamAV scanning, YARA threat detection &amp; TOTP MFA</li>
          <li>AES-256-GCM encrypted, RSA-signed verification reports</li>
        </ul>
      </div>
      <div className="auth-card">
        <div className="auth-tabs">
          <button className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setMfaRequired(false); setError('') }} type="button">
            Sign in
          </button>
          <button className={mode === 'register' ? 'active' : ''} onClick={() => { setMode('register'); setMfaRequired(false); setError('') }} type="button">
            Create account
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <label>
              Full name
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            </label>
          )}
          <label>
            Institutional email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required disabled={mfaRequired} />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} disabled={mfaRequired} />
          </label>
          {mfaRequired && (
            <label>
              Authenticator code (TOTP)
              <input
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                required
                maxLength={6}
                inputMode="numeric"
                placeholder="123456"
                autoFocus
              />
            </label>
          )}
          {error && <div className="form-error">{error}</div>}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Please wait…' : mfaRequired ? 'Verify & sign in' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>
        <p className="auth-hint">
          The first account created becomes the platform Administrator. After signing in, enable
          real TOTP-based MFA from the Security panel on your dashboard.
        </p>
      </div>
    </div>
  )
}
