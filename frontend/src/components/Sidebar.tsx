import { NavLink } from 'react-router-dom'
import {
  BarChart3, Brain, FileText, LayoutDashboard, MessageSquare, Users,
} from 'lucide-react'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/patient-flow', label: 'Patient Flow Analytics', icon: Users },
  { to: '/predictions', label: 'ML Predictions', icon: Brain },
  { to: '/reports', label: 'Reports & Queries', icon: FileText },
  { to: '/chatbot', label: 'AI Chatbot', icon: MessageSquare },
]

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <aside
      className="flex h-full w-[260px] shrink-0 flex-col"
      style={{ backgroundColor: 'var(--c-nav)', color: 'var(--c-nav-ink)' }}
    >
      {/* brand */}
      <div className="flex items-center gap-3 px-5 pb-6 pt-6">
        <div
          className="grid h-10 w-10 shrink-0 place-items-center rounded-[11px]"
          style={{ backgroundColor: 'var(--c-brand)' }}
        >
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
            <path d="M10 3h4v7h7v4h-7v7h-4v-7H3v-4h7z" fill="#ffffff" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="truncate text-[16px] font-bold leading-tight">HospitalFlow AI</p>
          <p className="text-[11px] leading-snug" style={{ color: 'var(--c-nav-mute)' }}>
            Smarter Insights. Healthier Tomorrow.
          </p>
        </div>
      </div>

      {/* nav */}
      <nav className="flex flex-col gap-1 px-3">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className="flex items-center gap-3 rounded-[10px] px-3 py-2.5 text-[13.5px] font-medium transition-colors"
            style={({ isActive }) => ({
              backgroundColor: isActive ? 'var(--c-brand)' : 'transparent',
              color: isActive ? '#ffffff' : 'var(--c-nav-mute)',
            })}
          >
            {({ isActive }) => (
              <>
                <Icon size={18} className="shrink-0" />
                <span className="truncate">{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* footer note */}
      <div className="mt-auto px-5 pb-6 pt-8">
        <div className="flex items-start gap-3">
          <BarChart3 size={20} className="mt-0.5 shrink-0" style={{ color: 'var(--c-nav-mute)' }} />
          <p className="text-[11.5px] leading-snug" style={{ color: 'var(--c-nav-mute)' }}>
            AI-Enabled Hospital Operations and Patient Flow Intelligence Platform
          </p>
        </div>
      </div>
    </aside>
  )
}
