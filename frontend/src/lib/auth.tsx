import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from 'react'
import type { ReactNode } from 'react'
import { api, setAuthToken, setUnauthorizedHandler } from '../api'

export interface User {
  username: string
  name: string
  role: string
}

interface AuthState {
  user: User | null
  checking: boolean
  signIn: (username: string, password: string) => Promise<void>
  signOut: () => void
}

const STORAGE_KEY = 'hf-token'
const AuthContext = createContext<AuthState | null>(null)

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    // private browsing, blocked storage: the app still works, the session
    // just will not survive a refresh.
    return null
  }
}

function writeStoredToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(STORAGE_KEY, token)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(true)

  // On first load, revive a saved session if its token is still valid.
  useEffect(() => {
    const token = readStoredToken()
    if (!token) {
      setChecking(false)
      return
    }
    setAuthToken(token)
    api.me()
      .then((u) => setUser(u))
      .catch(() => {
        writeStoredToken(null)
        setAuthToken(null)
      })
      .finally(() => setChecking(false))
  }, [])

  const signIn = useCallback(async (username: string, password: string) => {
    const res = await api.login(username, password)
    writeStoredToken(res.token)
    setAuthToken(res.token)
    setUser(res.user)
  }, [])

  const signOut = useCallback(() => {
    writeStoredToken(null)
    setAuthToken(null)
    setUser(null)
  }, [])

  // If any request comes back 401 (an expired session), drop to the login
  // screen rather than showing an error on every card.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      writeStoredToken(null)
      setAuthToken(null)
      setUser(null)
    })
    return () => setUnauthorizedHandler(null)
  }, [])

  const value = useMemo(
    () => ({ user, checking, signIn, signOut }),
    [user, checking, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
