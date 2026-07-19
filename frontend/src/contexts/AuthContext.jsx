import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { authFetch } from '../utils/api'

const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadUser() {
      try {
        const data = await authFetch('/auth/me', { method: 'GET' })
        setUser(data)
      } catch (error) {
        console.error('Failed to load current user', error)
      } finally {
        setLoading(false)
      }
    }
    loadUser()
  }, [])

  const value = useMemo(
    () => ({ user, setUser, loading }),
    [user, loading]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
