import { useEffect, useState } from 'react'
import { Download, Play, Table2 } from 'lucide-react'
import type { RangeCtx } from '../App'
import { api } from '../api'
import { useFetch } from '../lib/useFetch'
import { Card, ErrorBox, Loading } from '../components/ui'
import type { ReportResult } from '../types'

export default function Reports({ ctx }: { ctx: RangeCtx }) {
  const samples = useFetch(() => api.sampleQueries(), [])
  const [sql, setSql] = useState('SELECT DEPARTMENT, COUNT(*) AS visits\nFROM fact_encounters\nGROUP BY DEPARTMENT\nORDER BY visits DESC')
  const [result, setResult] = useState<ReportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { void run() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function run(query = sql) {
    setBusy(true)
    setError(null)
    try {
      setResult(await api.runQuery(query))
    } catch (e) {
      setError((e as Error).message)
      setResult(null)
    } finally {
      setBusy(false)
    }
  }

  function downloadCsv() {
    if (!result) return
    const head = result.columns.join(',')
    const body = result.rows
      .map((r) => result.columns.map((c) => JSON.stringify(r[c] ?? '')).join(','))
      .join('\n')
    const blob = new Blob([`${head}\n${body}`], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'hospitalflow-report.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-[24px] font-bold tracking-tight text-ink">Reports &amp; Queries</h1>
        <p className="mt-0.5 text-[13px] text-ink-soft">
          Run your own SQL against the hospital database. Read-only: only SELECT statements are accepted.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <Card title="Saved Reports" className="lg:col-span-1">
          {samples.loading ? <Loading /> : (
            <div className="space-y-1.5 pt-1">
              {(samples.data?.items ?? []).map((s) => (
                <button
                  key={s.title}
                  onClick={() => { setSql(s.sql); void run(s.sql) }}
                  className="flex w-full items-center gap-2 rounded-[10px] px-3 py-2 text-left text-[12.5px] text-ink-soft transition-colors hover:bg-surface-2"
                >
                  <Table2 size={14} style={{ color: 'var(--c-brand)' }} className="shrink-0" />
                  <span className="truncate">{s.title}</span>
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card
          title="SQL Editor"
          className="lg:col-span-3"
          action={
            <div className="flex gap-2">
              <button onClick={downloadCsv} disabled={!result} className="btn">
                <Download size={14} /> CSV
              </button>
              <button onClick={() => void run()} disabled={busy} className="btn-primary">
                <Play size={14} /> {busy ? 'Running…' : 'Run query'}
              </button>
            </div>
          }
        >
          <textarea
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            rows={7}
            spellCheck={false}
            aria-label="SQL query"
            className="font-mono !text-[12.5px] leading-relaxed"
            style={{ backgroundColor: 'var(--c-surface-2)' }}
          />
          <p className="mt-2 text-[11.5px] text-ink-mute">
            Tables: <code className="font-mono">fact_encounters</code>,{' '}
            <code className="font-mono">dim_patients</code>,{' '}
            <code className="font-mono">fact_conditions</code>,{' '}
            <code className="font-mono">fact_procedures</code>,{' '}
            <code className="font-mono">agg_daily_flow</code>,{' '}
            <code className="font-mono">agg_department</code>
          </p>
        </Card>
      </div>

      <Card
        title="Result"
        subtitle={result ? `${result.row_count} rows (first 200 shown)` : undefined}
        bodyClass="!px-0"
      >
        {busy ? <Loading label="Running query…" /> : error ? (
          <div className="px-5"><ErrorBox message={error} /></div>
        ) : !result || result.rows.length === 0 ? (
          <p className="px-5 py-6 text-center text-[13px] text-ink-mute">No rows returned.</p>
        ) : (
          <div className="max-h-[480px] overflow-auto">
            <table className="w-full text-[12.5px]">
              <thead className="sticky top-0" style={{ backgroundColor: 'var(--c-surface)' }}>
                <tr className="text-left text-ink-mute">
                  {result.columns.map((c) => (
                    <th key={c} className="border-b px-5 py-2.5 font-medium" style={{ borderColor: 'var(--c-border)' }}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((r, i) => (
                  <tr key={i}>
                    {result.columns.map((c) => (
                      <td key={c} className="border-b px-5 py-2 tabular-nums text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>
                        {r[c] === null || r[c] === undefined ? '—' : String(r[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
