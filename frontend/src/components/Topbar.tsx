import { useEffect, useRef, useState } from 'react'
import { Bell, LogOut, Menu, Moon, Search, Sun, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import type { EncounterRow } from '../types'
import { useAuth } from '../lib/auth'

export function Topbar({
  dark, onToggleTheme, onOpenMenu,
}: { dark: boolean; onToggleTheme: () => void; onOpenMenu: () => void }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<EncounterRow[]>([])
  const [open, setOpen] = useState(false)
  const boxRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { user, signOut } = useAuth()

  useEffect(() => {
    if (q.trim().length < 2) {
      setResults([])
      return
    }
    const t = setTimeout(() => {
      api.search(q.trim())
        .then((r) => { setResults(r.items); setOpen(true) })
        .catch(() => setResults([]))
    }, 300)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!q.trim()) return
    if (results.length === 0) navigate(`/chatbot?q=${encodeURIComponent(q)}`)
  }

  return (
    <header
      className="sticky top-0 z-30 flex h-[66px] items-center gap-3 border-b px-4 md:px-6"
      style={{ backgroundColor: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
    >
      <button
        onClick={onOpenMenu}
        className="btn h-9 w-9 !px-0 lg:hidden"
        aria-label="Open navigation menu"
      >
        <Menu size={18} />
      </button>

      <div ref={boxRef} className="relative flex-1 max-w-[720px]">
        <form onSubmit={submit}>
          <Search
            size={16}
            className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2"
            style={{ color: 'var(--c-ink-mute)' }}
          />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onFocus={() => results.length && setOpen(true)}
            placeholder="Search patients, encounters, or ask a question…"
            aria-label="Search"
            className="!rounded-[11px] !py-2.5 !pl-10"
            style={{ backgroundColor: 'var(--c-surface-2)' }}
          />
        </form>

        {open && results.length > 0 && (
          <div
            className="absolute left-0 right-0 top-[46px] z-40 max-h-[320px] overflow-auto rounded-xl2 border shadow-pop"
            style={{ backgroundColor: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
          >
            {results.map((r) => (
              <div
                key={r.ENCOUNTER_ID}
                className="flex items-center justify-between gap-3 border-b px-4 py-2.5 text-[13px] last:border-0"
                style={{ borderColor: 'var(--c-border)' }}
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-ink">{r.FULL_NAME}</p>
                  <p className="truncate text-[11.5px] text-ink-mute">
                    {r.DEPARTMENT} · {r.ENCOUNTERCLASS} · {r.VISIT_DATE}
                  </p>
                </div>
                <span className="shrink-0 text-[11.5px] text-ink-mute">{r.AGE}y</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button
          onClick={onToggleTheme}
          className="btn h-9 w-9 !px-0"
          aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
          title={dark ? 'Light mode' : 'Dark mode'}
        >
          {dark ? <Sun size={17} /> : <Moon size={17} />}
        </button>
        <button className="btn h-9 w-9 !px-0" aria-label="Notifications">
          <Bell size={17} />
        </button>
        <div className="flex items-center gap-2.5 pl-1">
          <div
            className="grid h-9 w-9 place-items-center rounded-full"
            style={{ backgroundColor: 'var(--c-brand-soft)', color: 'var(--c-brand)' }}
          >
            <User size={17} />
          </div>
          <div className="hidden leading-tight sm:block">
            <p className="text-[13px] font-semibold text-ink">{user?.name ?? 'Guest'}</p>
            <p className="text-[11px] text-ink-mute">{user?.role ?? ''}</p>
          </div>
          <button
            onClick={signOut}
            className="btn h-9 w-9 !px-0"
            aria-label="Sign out"
            title="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </header>
  )
}
