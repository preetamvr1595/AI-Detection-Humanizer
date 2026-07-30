import { useState } from 'react'
import api from '../api/client'
import Layout from '../components/Layout'
import { useAuth } from '../context/AuthContext'

export default function SecurityPage() {
  const { user } = useAuth()
  const [setupData, setSetupData] = useState(null)
  const [code, setCode] = useState('')
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [mfaEnabled, setMfaEnabled] = useState(user?.mfa_enabled || false)

  async function startSetup() {
    setError('')
    const { data } = await api.post('/auth/mfa/setup')
    setSetupData(data)
  }

  async function confirmEnable() {
    setError('')
    try {
      await api.post('/auth/mfa/enable', null, { params: { code } })
      setMfaEnabled(true)
      setStatus('MFA enabled — you will need a code from your authenticator app on every future sign-in.')
      setSetupData(null)
      setCode('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code')
    }
  }

  async function disable() {
    await api.post('/auth/mfa/disable')
    setMfaEnabled(false)
    setStatus('MFA disabled.')
  }

  return (
    <Layout>
      <div className="page-header">
        <h1>Security</h1>
        <p>Real RFC 6238 TOTP multi-factor authentication — works with Google Authenticator, Authy, or any standard authenticator app.</p>
      </div>

      <div className="security-card">
        <div className="security-row">
          <div>
            <div className="security-label">Multi-factor authentication</div>
            <div className="security-sub">{mfaEnabled ? 'Enabled — a code is required on every sign-in.' : 'Not enabled on this account.'}</div>
          </div>
          <div className={`status-pill ${mfaEnabled ? 'status-complete' : 'status-queued'}`}>
            {mfaEnabled ? 'ON' : 'OFF'}
          </div>
        </div>

        {status && <p className="security-status">{status}</p>}
        {error && <div className="form-error">{error}</div>}

        {!mfaEnabled && !setupData && (
          <button className="btn-primary" onClick={startSetup}>Set up MFA</button>
        )}

        {!mfaEnabled && setupData && (
          <div className="mfa-setup">
            <p className="security-sub">Scan this QR code in your authenticator app, then enter the 6-digit code it shows:</p>
            <img
              className="mfa-qr"
              src={`data:image/png;base64,${setupData.qr_code_png_base64}`}
              alt="MFA QR code"
            />
            <p className="security-sub">Or enter this secret manually: <code>{setupData.secret}</code></p>
            <div className="mfa-confirm-row">
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="123456"
                maxLength={6}
                inputMode="numeric"
              />
              <button className="btn-primary" onClick={confirmEnable}>Confirm & enable</button>
            </div>
          </div>
        )}

        {mfaEnabled && (
          <button className="btn-ghost" onClick={disable}>Disable MFA</button>
        )}
      </div>

      <h2 className="section-title">What's real here</h2>
      <p className="security-sub">
        This is genuine RFC 6238 TOTP — the same algorithm your bank or GitHub uses. Codes are
        generated locally by your authenticator app from a shared secret and verified server-side
        with a real cryptographic check, not a mock. See the project README for how this maps to
        a production Keycloak deployment.
      </p>
    </Layout>
  )
}
