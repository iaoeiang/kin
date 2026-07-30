'use client'

import { useState, createContext, useContext, useEffect } from 'react'

interface AuthState {
  token: string
  userId: string
  email: string
  displayName: string
}

const AuthContext = createContext<{
  auth: AuthState | null
  setAuth: (a: AuthState | null) => void
  apiUrl: string
}>({ auth: null, setAuth: () => {}, apiUrl: 'http://localhost:8000' })

export function useAuth() { return useContext(AuthContext) }

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(null)
  useEffect(() => {
    const saved = localStorage.getItem('agentnet_auth')
    if (saved) try { setAuth(JSON.parse(saved)) } catch {}
  }, [])
  return (
    <AuthContext.Provider value={{ auth, setAuth, apiUrl: API }}>
      {children}
    </AuthContext.Provider>
  )
}

export async function apiFetch(path: string, opts: RequestInit = {}) {
  const token = localStorage.getItem('agentnet_auth')
    ? JSON.parse(localStorage.getItem('agentnet_auth')!).token
    : ''
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export { API }
