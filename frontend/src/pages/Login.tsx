import { useEffect, useState } from 'react'
import { BarChart3, Brain, Eye, EyeOff, Loader2, LockKeyhole, MessageSquare, User } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../lib/auth'

interface DemoAccount {
  username: string
  password: string
  role: string
}

export default function Login() {
  const { signIn } = useAuth()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [accounts, setAccounts] = useState<DemoAccount[]>([])

  useEffect(() => {
    api.demoAccounts()
      .then((r) => setAccounts(r.items))
      .catch(() => setAccounts([]))
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await signIn(username, password)
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  function useAccount(a: DemoAccount) {
    setUsername(a.username)
    setPassword(a.password)
    setError(null)
  }

  return (
    <div className="flex min-h-full">
      {/* ------------------------------------------- brand panel (desktop) */}
      <div
        className="hidden w-[46%] max-w-[620px] flex-col justify-between p-12 lg:flex"
        style={{ backgroundColor: 'var(--c-nav)', color: 'var(--c-nav-ink)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="grid h-11 w-11 shrink-0 place-items-center rounded-[12px]"
            style={{ backgroundColor: 'var(--c-brand)' }}
          >
            <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
              <path d="M10 3h4v7h7v4h-7v7h-4v-7H3v-4h7z" fill="#ffffff" />
            </svg>
          </div>
          <div>
            <p className="text-[18px] font-bold leading-tight">HospitalFlow AI</p>
            <p className="text-[12px]" style={{ color: 'var(--c-nav-mute)' }}>
              Smarter Insights. Healthier Tomorrow.
            </p>
          </div>
        </div>

        <div>
          <h1 className="text-[32px] font-bold leading-tight">
            Turn hospital data into decisions.
          </h1>
          <p className="mt-3 max-w-[420px] text-[14px]" style={{ color: 'var(--c-nav-mute)' }}>
            One place for patient flow, department performance and machine-learning
            forecasts — so beds, staff and resources can be planned before the
            pressure arrives.
          </p>

          <ul className="mt-8 space-y-4">
            {[
              { icon: BarChart3, title: 'Live operational KPIs', body: 'Visits, admissions, discharges, length of stay and revenue.' },
              { icon: Brain, title: 'Predictive models', body: 'Admission forecasting and length-of-stay prediction.' },
              { icon: MessageSquare, title: 'Ask in plain English', body: 'The assistant answers from the hospital database.' },
            ].map(({ icon: Icon, title, body }) => (
              <li key={title} className="flex gap-3">
                <span
                  className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-[9px]"
                  style={{ backgroundColor: 'var(--c-nav-soft)' }}
                >
                  <Icon size={16} style={{ color: 'var(--c-brand)' }} />
                </span>
                <div>
                  <p className="text-[13.5px] font-semibold">{title}</p>
                  <p className="text-[12.5px]" style={{ color: 'var(--c-nav-mute)' }}>{body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-[11.5px]" style={{ color: 'var(--c-nav-mute)' }}>
          AI-Enabled Hospital Operational and Patient-Flow BI Platform
        </p>
      </div>

      {/* ------------------------------------------------------ form panel */}
      <div className="flex flex-1 items-center justify-center px-5 py-10">
        <div className="w-full max-w-[400px]">
          {/* small-screen brand */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div
              className="grid h-10 w-10 shrink-0 place-items-center rounded-[11px]"
              style={{ backgroundColor: 'var(--c-brand)' }}
            >
              <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                <path d="M10 3h4v7h7v4h-7v7h-4v-7H3v-4h7z" fill="#ffffff" />
              </svg>
            </div>
            <div>
              <p className="text-[16px] font-bold leading-tight text-ink">HospitalFlow AI</p>
              <p className="text-[11px] text-ink-mute">Smarter Insights. Healthier Tomorrow.</p>
            </div>
          </div>

          <h2 className="text-[22px] font-bold tracking-tight text-ink">Sign in</h2>
          <p className="mt-1 text-[13px] text-ink-soft">
            Use your hospital account to open the dashboard.
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <label className="block">
              <span className="mb-1.5 block text-[12.5px] font-medium text-ink-soft">Username</span>
              <div className="relative">
                <User
                  size={16}
                  className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--c-ink-mute)' }}
                />
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  autoFocus
                  required
                  className="!py-2.5 !pl-10"
                />
              </div>
            </label>

            <label className="block">
              <span className="mb-1.5 block text-[12.5px] font-medium text-ink-soft">Password</span>
              <div className="relative">
                <LockKeyhole
                  size={16}
                  className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--c-ink-mute)' }}
                />
                <input
                  type={show ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  className="!py-2.5 !pl-10 !pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShow((v) => !v)}
                  aria-label={show ? 'Hide password' : 'Show password'}
                  className="absolute right-2.5 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-md"
                  style={{ color: 'var(--c-ink-mute)' }}
                >
                  {show ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </label>

            {error && (
              <p
                className="rounded-[10px] px-3.5 py-2.5 text-[12.5px]"
                style={{ backgroundColor: 'var(--c-brand-soft)', color: 'var(--c-bad)' }}
                role="alert"
              >
                {error}
              </p>
            )}

            <button type="submit" className="btn-primary w-full !py-2.5" disabled={busy}>
              {busy ? <><Loader2 size={15} className="animate-spin" /> Signing in…</> : 'Sign in'}
            </button>
          </form>

          {accounts.length > 0 && (
            <div
              className="mt-7 rounded-xl2 border p-4"
              style={{ borderColor: 'var(--c-border)', backgroundColor: 'var(--c-surface-2)' }}
            >
              <p className="text-[12px] font-semibold text-ink">Demo accounts</p>
              <p className="mt-0.5 text-[11.5px] text-ink-mute">
                Click one to fill the form.
              </p>
              <div className="mt-3 space-y-1.5">
                {accounts.map((a) => (
                  <button
                    key={a.username}
                    type="button"
                    onClick={() => useAccount(a)}
                    className="flex w-full items-center justify-between gap-3 rounded-[9px] border px-3 py-2 text-left transition-colors"
                    style={{ borderColor: 'var(--c-border)', backgroundColor: 'var(--c-surface)' }}
                  >
                    <span className="min-w-0">
                      <span className="block truncate font-mono text-[12px] text-ink">
                        {a.username} / {a.password}
                      </span>
                      <span className="block truncate text-[11px] text-ink-mute">{a.role}</span>
                    </span>
                    <span className="shrink-0 text-[11px]" style={{ color: 'var(--c-brand)' }}>
                      Use
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <p className="mt-6 text-center text-[11px] text-ink-mute">
            Demo sign-in for the project. Passwords live in{' '}
            <code className="font-mono">.env</code>, not in a user database.
          </p>
        </div>
      </div>
    </div>
  )
}
