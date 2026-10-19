export const nf = new Intl.NumberFormat('en-US')

export function fmtNumber(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return nf.format(Math.round(v))
}

export function fmtMoney(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  return `$${nf.format(Math.round(v))}`
}

export function fmtDays(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return `${v.toFixed(1)} days`
}

export function fmtValue(v: number, format: string): string {
  if (format === 'currency') return fmtMoney(v)
  if (format === 'days') return fmtDays(v)
  return fmtNumber(v)
}

export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return `${v.toFixed(digits)}%`
}

export function prettyDate(iso: string): string {
  if (!iso) return '-'
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  })
}

export function shortDate(iso: string): string {
  if (!iso) return '-'
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

/**
 * Date maths on a plain YYYY-MM-DD string.
 * Everything is done in UTC on purpose: parsing as local time would shift
 * the day for anyone not on UTC (IST would land a day early).
 */
export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}
