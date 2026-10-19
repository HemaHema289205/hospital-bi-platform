import { useCallback, useEffect, useMemo, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import Dashboard from './pages/Dashboard'
import PatientFlow from './pages/PatientFlow'
import Predictions from './pages/Predictions'
import Reports from './pages/Reports'
import Chatbot from './pages/Chatbot'
import Login from './pages/Login'
import { useAuth } from './lib/auth'
import { api } from './api'
import { addDays } from './lib/format'

export interface RangeCtx {
  start: string
  end: string
  days: number
  setDays: (d: number) => void
  dark: boolean
}

export default function App() {
  const { user, checking } = useAuth()
  const [dark, setDark] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [days, setDays] = useState(30)
  const [maxDate, setMaxDate] = useState<string>('')

  /* ---- theme: remembered per browser, falls back to the OS setting ---- */
  useEffect(() => {
    let initial = false
    try {
      const saved = localStorage.getItem('hf-theme')
      initial = saved
        ? saved === 'dark'
        : window.matchMedia('(prefers-color-scheme: dark)').matches
    } catch {
      initial = false
    }
    setDark(initial)
  }, [])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    try {
      localStorage.setItem('hf-theme', dark ? 'dark' : 'light')
    } catch {
      /* private mode - the app still works, it just will not remember */
    }
  }, [dark])

  /* ---- the data has its own "today", so ranges are anchored to it ---- */
  useEffect(() => {
    if (!user) return
    api.meta()
      .then((m) => setMaxDate(m.data_range.max_date))
      .catch(() => setMaxDate(new Date().toISOString().slice(0, 10)))
  }, [user])

  const range = useMemo(() => {
    const end = maxDate || new Date().toISOString().slice(0, 10)
    return { start: addDays(end, -(days - 1)), end }
  }, [maxDate, days])

  const ctx: RangeCtx = {
    start: range.start,
    end: range.end,
    days,
    setDays,
    dark,
  }

  const closeMenu = useCallback(() => setMenuOpen(false), [])

  // reviving a saved session
  if (checking) return <Splash label="Starting HospitalFlow AI…" />

  // not signed in -> the login screen is the whole app
  if (!user) return <Login />

  if (!maxDate) return <Splash label="Connecting to HospitalFlow AI…" />

  return (
    <div className="flex h-full">
      {/* desktop sidebar */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* mobile drawer */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0"
            style={{ backgroundColor: 'rgba(8, 15, 28, 0.55)' }}
            onClick={closeMenu}
          />
          <div className="absolute left-0 top-0 h-full">
            <Sidebar onNavigate={closeMenu} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          dark={dark}
          onToggleTheme={() => setDark((d) => !d)}
          onOpenMenu={() => setMenuOpen(true)}
        />
        <main className="flex-1 overflow-y-auto px-4 py-5 md:px-6">
          <Routes>
            <Route path="/" element={<Dashboard ctx={ctx} />} />
            <Route path="/patient-flow" element={<PatientFlow ctx={ctx} />} />
            <Route path="/predictions" element={<Predictions ctx={ctx} />} />
            <Route path="/reports" element={<Reports ctx={ctx} />} />
            <Route path="/chatbot" element={<Chatbot ctx={ctx} />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

function Splash({ label }: { label: string }) {
  return (
    <div className="grid h-full place-items-center text-ink-mute">
      <div className="text-center">
        <div
          className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2"
          style={{ borderColor: 'var(--c-brand)', borderTopColor: 'transparent' }}
        />
        {label}
      </div>
    </div>
  )
}
