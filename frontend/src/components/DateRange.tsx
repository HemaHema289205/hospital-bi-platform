import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'
import type { RangeCtx } from '../App'
import { addDays, prettyDate } from '../lib/format'

export const PRESETS = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
  { label: 'Last 12 months', days: 365 },
]

const dateInput =
  '!w-auto !border-0 !bg-transparent !px-0 !py-0 text-[12.5px] font-medium text-ink'

export function DateRange({ ctx }: { ctx: RangeCtx }) {
  const { start, end, days, mode, setDays, setCustom, minDate, maxDate } = ctx

  const selectValue = mode === 'preset' ? String(days) : mode

  function onSelect(v: string) {
    if (v === 'day') setCustom('day', end, end)
    else if (v === 'custom') setCustom('custom', start, end)
    else setDays(Number(v))
  }

  // step one day back / forward in single-day mode, staying inside the data
  function step(by: number) {
    const d = addDays(start, by)
    if (d < minDate || d > maxDate) return
    setCustom('day', d, d)
  }

  return (
    <div
      className="flex flex-wrap items-center gap-2 rounded-[11px] border px-3 py-2"
      style={{ backgroundColor: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
    >
      <Calendar size={15} style={{ color: 'var(--c-ink-mute)' }} />

      {mode === 'preset' && (
        <span className="hidden text-[12.5px] font-medium text-ink sm:inline">
          {prettyDate(start)} – {prettyDate(end)}
        </span>
      )}

      {mode === 'day' && (
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => step(-1)}
            disabled={start <= minDate}
            className="grid h-6 w-6 place-items-center rounded-md text-ink-soft disabled:opacity-30"
            aria-label="Previous day"
            title="Previous day"
          >
            <ChevronLeft size={15} />
          </button>
          <input
            type="date"
            value={start}
            min={minDate}
            max={maxDate}
            onChange={(e) => e.target.value && setCustom('day', e.target.value, e.target.value)}
            aria-label="Choose a date"
            className={dateInput}
          />
          <button
            type="button"
            onClick={() => step(1)}
            disabled={start >= maxDate}
            className="grid h-6 w-6 place-items-center rounded-md text-ink-soft disabled:opacity-30"
            aria-label="Next day"
            title="Next day"
          >
            <ChevronRight size={15} />
          </button>
        </div>
      )}

      {mode === 'custom' && (
        <div className="flex items-center gap-1.5">
          <input
            type="date"
            value={start}
            min={minDate}
            max={maxDate}
            onChange={(e) => e.target.value && setCustom('custom', e.target.value, end)}
            aria-label="Start date"
            className={dateInput}
          />
          <span className="text-ink-mute">–</span>
          <input
            type="date"
            value={end}
            min={minDate}
            max={maxDate}
            onChange={(e) => e.target.value && setCustom('custom', start, e.target.value)}
            aria-label="End date"
            className={dateInput}
          />
        </div>
      )}

      <select
        value={selectValue}
        onChange={(e) => onSelect(e.target.value)}
        aria-label="Select reporting period"
        className="!w-auto !border-0 !bg-transparent !px-1 !py-0 text-[12.5px] font-medium"
        style={{ color: 'var(--c-brand)' }}
      >
        {PRESETS.map((p) => (
          <option key={p.days} value={p.days}>{p.label}</option>
        ))}
        <option value="day">Single day</option>
        <option value="custom">Custom range</option>
      </select>
    </div>
  )
}
