import { NavLink } from 'react-router-dom'
import {
  Brain, FileText, Hospital, LayoutDashboard, MessageSquare, Users,
} from 'lucide-react'
import Logo from './Logo'

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
      className="flex h-full w-[260px] shrink-0 flex-col border-r"
      style={{
        backgroundColor: 'var(--c-side)',
        borderColor: 'var(--c-side-border)',
        color: 'var(--c-side-ink)',
      }}
    >
      {/* brand */}
      <div className="flex items-center gap-3 px-5 pb-6 pt-6">
        <Logo size={42} />
        <div className="min-w-0">
          <p className="truncate text-[16px] font-bold leading-tight">HospitalFlow AI</p>
          <p className="text-[11px] leading-snug" style={{ color: 'var(--c-side-mute)' }}>
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
              backgroundColor: isActive ? 'var(--c-side-active)' : 'transparent',
              color: isActive ? 'var(--c-side-active-ink)' : 'var(--c-side-mute)',
            })}
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={18}
                  className="shrink-0"
                  style={{ color: isActive ? 'var(--c-side-active-ink)' : 'var(--c-side-icon)' }}
                />
                <span className="truncate">{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* footer note */}
      <div className="mt-auto px-5 pb-6 pt-8">
        <div className="flex items-start gap-3">
          <Hospital size={22} className="mt-0.5 shrink-0" style={{ color: 'var(--c-brand)' }} />
          <p className="text-[11.5px] leading-snug" style={{ color: 'var(--c-side-mute)' }}>
            AI-Enabled Hospital Operations and Patient Flow Intelligence Platform
          </p>
        </div>
      </div>
    </aside>
  )
}
