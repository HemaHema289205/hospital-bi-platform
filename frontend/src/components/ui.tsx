import type { ReactNode } from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

/* ------------------------------------------------------------ Card */
export function Card({
  title, subtitle, icon: Icon, action, children, className = '', bodyClass = '',
}: {
  title?: string
  subtitle?: string
  icon?: LucideIcon
  action?: ReactNode
  children: ReactNode
  className?: string
  bodyClass?: string
}) {
  return (
    <section className={`card flex flex-col ${className}`}>
      {(title || action) && (
        <header className="flex items-start justify-between gap-3 px-5 pt-4 pb-2">
          <div className="flex items-start gap-2.5">
            {Icon && (
              <span
                className="grid h-8 w-8 shrink-0 place-items-center rounded-full"
                style={{ backgroundColor: 'var(--c-brand-soft)', color: 'var(--c-brand)' }}
              >
                <Icon size={16} />
              </span>
            )}
            <div className={Icon ? 'pt-1' : ''}>
              {title && <h2 className="card-title">{title}</h2>}
              {subtitle && <p className="text-[12px] text-ink-mute mt-0.5">{subtitle}</p>}
            </div>
          </div>
          {action}
        </header>
      )}
      <div className={`px-5 pb-5 pt-1 flex-1 ${bodyClass}`}>{children}</div>
    </section>
  )
}

/* --------------------------------------------------------- Loading */
export function Loading({ label = 'Loading…', className = '' }: { label?: string; className?: string }) {
  return (
    <div className={`flex items-center justify-center gap-2 text-ink-mute text-[13px] py-10 ${className}`}>
      <Loader2 size={16} className="animate-spin" />
      {label}
    </div>
  )
}

export function Skeleton({ className = 'h-24' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

/* ----------------------------------------------------------- Error */
export function ErrorBox({ message }: { message: string }) {
  return (
    <div
      className="flex items-start gap-2.5 rounded-xl2 p-4 text-[13px]"
      style={{ backgroundColor: 'var(--c-brand-soft)', color: 'var(--c-ink)' }}
    >
      <AlertTriangle size={16} style={{ color: 'var(--c-warn)' }} className="mt-0.5 shrink-0" />
      <div>
        <p className="font-medium">Could not load this data</p>
        <p className="text-ink-soft mt-0.5">{message}</p>
        <p className="text-ink-mute mt-1.5">
          Is the backend running? Start it with{' '}
          <code className="font-mono">python -m uvicorn backend.main:app --reload</code>
        </p>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------ Badge */
const STATUS_TONE: Record<string, { bg: string; fg: string }> = {
  Admitted: { bg: '#e8f7ee', fg: '#15803d' },
  Discharged: { bg: '#eaf2fe', fg: '#1552bd' },
  Completed: { bg: '#f1f5f9', fg: '#475569' },
}

export function StatusBadge({ status }: { status: string }) {
  const tone = STATUS_TONE[status] ?? STATUS_TONE.Completed
  return (
    <span className="chip" style={{ backgroundColor: tone.bg, color: tone.fg }}>
      {status}
    </span>
  )
}

/* -------------------------------------------------------- Delta tag */
export function Delta({ pct, suffix = 'vs last period' }: { pct: number; suffix?: string }) {
  const up = pct >= 0
  const color = up ? 'var(--c-ok)' : 'var(--c-bad)'
  return (
    <div className="flex items-baseline gap-1.5 text-[12px]">
      <span className="font-semibold" style={{ color }}>
        {up ? '↑' : '↓'} {Math.abs(pct).toFixed(1)}%
      </span>
      <span className="text-ink-mute">{suffix}</span>
    </div>
  )
}

/* --------------------------------------------------------- Bar line */
export function MeterRow({
  label, pct, value, color,
}: { label: string; pct: number; value: string; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-[42%] shrink-0 truncate text-[13px] text-ink-soft">{label}</span>
      <div
        className="h-2 flex-1 overflow-hidden rounded-full"
        style={{ backgroundColor: 'var(--c-track)' }}
        role="img"
        aria-label={`${label}: ${value}`}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(100, Math.max(2, pct))}%`, backgroundColor: color }}
        />
      </div>
      <span className="w-12 shrink-0 text-right text-[12px] font-medium tabular-nums text-ink">
        {value}
      </span>
    </div>
  )
}
