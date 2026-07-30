import { createContext, useContext, useState, useCallback } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('scholarshield_user')
    return stored ? JSON.parse(stored) : null
  })

  const login = useCallback(async (email, password, totp_code) => {
    const { data } = await api.post('/auth/login', { email, password, totp_code: totp_code || undefined })
    localStorage.setItem('scholarshield_token', data.access_token)
    localStorage.setItem('scholarshield_user', JSON.stringify(data.user))
    setUser(data.user)
    return data.user
  }, [])

  const register = useCallback(async (full_name, email, password) => {
    const { data } = await api.post('/auth/register', { full_name, email, password })
    localStorage.setItem('scholarshield_token', data.access_token)
    localStorage.setItem('scholarshield_user', JSON.stringify(data.user))
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('scholarshield_token')
    localStorage.removeItem('scholarshield_user')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
