import { Activity, BedDouble, DollarSign, Timer, UserRound } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { KpiCardData } from '../types'
import { fmtValue } from '../lib/format'
import { toneFor } from '../lib/colors'

const ICONS: Record<string, LucideIcon> = {
  total_visits: UserRound,
  admissions: BedDouble,
  discharges: Activity,
  avg_length_of_stay: Timer,
  total_revenue: DollarSign,
}

export function KpiCard({ card, index, dark }: { card: KpiCardData; index: number; dark: boolean }) {
  const tone = toneFor(index)
  const Icon = ICONS[card.key] ?? Activity
  const up = card.change_pct >= 0
  // Length of stay going DOWN is good news, so the arrow colour flips.
  const goodWhenDown = card.key === 'avg_length_of_stay'
  const positive = goodWhenDown ? !up : up

  return (
    <article
      className="rounded-xl2 border p-4"
      style={{
        backgroundColor: dark ? tone.bgDark : tone.bg,
        borderColor: dark ? 'var(--c-border)' : tone.ring,
      }}
    >
      <div className="flex items-start gap-3">
        <div
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full"
          style={{ backgroundColor: dark ? 'rgba(255,255,255,0.08)' : '#ffffff' }}
        >
          <Icon size={20} color={tone.icon} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[12.5px] font-medium text-ink-soft">{card.label}</p>
          <p className="mt-1 text-[26px] font-bold leading-none tracking-tight text-ink">
            {fmtValue(card.value, card.format)}
          </p>
          <div className="mt-2 flex flex-col">
            <span
              className="text-[12px] font-semibold"
              style={{ color: positive ? 'var(--c-ok)' : 'var(--c-bad)' }}
            >
              {up ? '↑' : '↓'} {Math.abs(card.change_pct).toFixed(1)}%
            </span>
            <span className="text-[11px] text-ink-mute">vs previous period</span>
          </div>
        </div>
      </div>
    </article>
  )
}
