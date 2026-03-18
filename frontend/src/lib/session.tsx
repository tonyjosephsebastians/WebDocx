/* eslint-disable react-refresh/only-export-components */

import { createContext, useContext, useMemo, useState, type PropsWithChildren } from 'react'

import type { AuthUser, TokenResponse } from './types'

const STORAGE_KEY = 'word-workspace-session'

type SessionContextValue = {
  ready: boolean
  token: string | null
  user: AuthUser | null
  applyAuthResponse: (response: TokenResponse) => void
  logout: () => void
}

const SessionContext = createContext<SessionContextValue | null>(null)

function readInitialSession() {
  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (raw) {
    try {
      return JSON.parse(raw) as { token: string | null; user: AuthUser | null }
    } catch {
      window.localStorage.removeItem(STORAGE_KEY)
    }
  }
  return { token: null, user: null }
}

export function SessionProvider({ children }: PropsWithChildren) {
  const [ready] = useState(true)
  const [token, setToken] = useState<string | null>(() => readInitialSession().token)
  const [user, setUser] = useState<AuthUser | null>(() => readInitialSession().user)

  const value = useMemo<SessionContextValue>(
    () => ({
      ready,
      token,
      user,
      applyAuthResponse(response) {
        setToken(response.access_token)
        setUser(response.user)
        window.localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ token: response.access_token, user: response.user }),
        )
      },
      logout() {
        setToken(null)
        setUser(null)
        window.localStorage.removeItem(STORAGE_KEY)
      },
    }),
    [ready, token, user],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession() {
  const context = useContext(SessionContext)
  if (!context) {
    throw new Error('useSession must be used inside SessionProvider')
  }
  return context
}
