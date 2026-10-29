import {
  Area, AreaChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import {
  Activity, BriefcaseMedical, CalendarDays, ClipboardList, LineChart as LineChartIcon,
  TrendingDown, TrendingUp, Users,
} from 'lucide-react'
import type { RangeCtx } from '../App'
import { api } from '../api'
import { useFetch } from '../lib/useFetch'
import { Card, ErrorBox, Loading, MeterRow, Skeleton, StatusBadge } from '../components/ui'
import { KpiCard } from '../components/KpiCard'
import { DateRange } from '../components/DateRange'
import { ChatPanel } from '../components/ChatPanel'
import { CHART, SERIES } from '../lib/colors'
import { fmtNumber } from '../lib/format'

const GENDER_COLORS: Record<string, string> = {
  Male: CHART.blue,
  Female: CHART.pink,
  Other: CHART.slate,
}

export default function Dashboard({ ctx }: { ctx: RangeCtx }) {
  const { start, end, days, setDays, dark } = ctx

  const kpis = useFetch(() => api.kpis(start, end), [start, end])
  const flow = useFetch(() => api.patientFlow(start, end), [start, end])
  const demo = useFetch(() => api.demographics(start, end), [start, end])
  const conds = useFetch(() => api.conditions(start, end, 5), [start, end])
  const recent = useFetch(() => api.recent(6), [])
  const fc = useFetch(() => api.forecast(14), [])
  // A "typical" inpatient, so the dashboard can show a live LOS prediction
  const losDemo = useFetch(
    () => api.predictLos({
      age: 55, gender: 'Female', department: 'General Medicine',
      encounter_class: 'inpatient', wait_minutes: 30,
    }),
    [],
  )

  const axis = { fontSize: 11, fill: 'var(--c-ink-mute)' }

  return (
    <div className="space-y-4">
      {/* ------------------------------------------------ page header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[24px] font-bold tracking-tight text-ink">
            Hospital Operations Dashboard
          </h1>
          <p className="mt-0.5 text-[13px] text-ink-soft">
            Insights into patient flow, hospital performance and predictions
          </p>
        </div>
        <DateRange start={start} end={end} days={days} onChangeDays={setDays} />
      </div>

      {/* --------------------------------------------------- KPI row */}
      {kpis.error && <ErrorBox message={kpis.error} />}
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {kpis.loading
          ? Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-[108px]" />)
          : kpis.data?.cards.map((c, i) => (
              <KpiCard key={c.key} card={c} index={i} dark={dark} />
            ))}
      </div>

      {/* ------------------------------------------ main grid + chat */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="space-y-4 xl:col-span-9">
          {/* trend + demographics */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
            <Card
              title="Patient Flow Trend"
              icon={LineChartIcon}
              className="lg:col-span-3"
              action={
                <div className="flex flex-wrap items-center gap-3 text-[11.5px] text-ink-soft">
                  {[
                    { k: 'Visits', c: CHART.blue },
                    { k: 'Admissions', c: CHART.green },
                    { k: 'Discharges', c: CHART.violet },
                  ].map((l) => (
                    <span key={l.k} className="flex items-center gap-1.5">
                      <span
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ backgroundColor: l.c }}
                      />
                      {l.k}
                    </span>
                  ))}
                </div>
              }
            >
              {flow.loading ? (
                <Loading />
              ) : flow.error ? (
                <ErrorBox message={flow.error} />
              ) : (
                <ResponsiveContainer width="100%" height={248}>
                  <LineChart data={flow.data?.series ?? []} margin={{ top: 8, right: 10, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke="var(--c-grid)" vertical={false} />
                    <XAxis dataKey="label" tick={axis} tickLine={false} axisLine={false} minTickGap={24} />
                    <YAxis tick={axis} tickLine={false} axisLine={false} width={52} />
                    <Tooltip />
                    <Line type="monotone" dataKey="visits" name="Visits" stroke={CHART.blue} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="admissions" name="Admissions" stroke={CHART.green} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="discharges" name="Discharges" stroke={CHART.violet} strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Card>

            <Card title="Patient Demographics" icon={Users} className="lg:col-span-2">
              {demo.loading ? (
                <Loading />
              ) : demo.error ? (
                <ErrorBox message={demo.error} />
              ) : (
                <div className="flex items-center gap-4">
                  <div className="relative h-[190px] w-[190px] shrink-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={demo.data?.gender ?? []}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={58}
                          outerRadius={88}
                          paddingAngle={2}
                          stroke="none"
                        >
                          {(demo.data?.gender ?? []).map((g) => (
                            <Cell key={g.name} fill={GENDER_COLORS[g.name] ?? CHART.slate} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="pointer-events-none absolute inset-0 grid place-items-center">
                      <div className="text-center">
                        <p className="text-[20px] font-bold leading-none text-ink">
                          {fmtNumber(demo.data?.total ?? 0)}
                        </p>
                        <p className="mt-1 text-[11px] text-ink-mute">Total Visits</p>
                      </div>
                    </div>
                  </div>
                  <ul className="flex-1 space-y-2.5">
                    {(demo.data?.gender ?? []).map((g) => (
                      <li key={g.name} className="flex items-center gap-2 text-[12.5px]">
                        <span
                          className="inline-block h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: GENDER_COLORS[g.name] ?? CHART.slate }}
                        />
                        <span className="flex-1 text-ink-soft">{g.name}</span>
                        <span className="font-semibold tabular-nums text-ink">{g.pct}%</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          </div>

          {/* conditions + predictions */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card title="Top Medical Conditions" icon={BriefcaseMedical}>
              {conds.loading ? (
                <Loading />
              ) : conds.error ? (
                <ErrorBox message={conds.error} />
              ) : (
                <div className="space-y-3 pt-2">
                  {(conds.data?.items ?? []).map((c, i) => (
                    <MeterRow
                      key={c.name}
                      label={c.name}
                      pct={c.pct}
                      value={`${c.pct}%`}
                      color={c.name === 'Other' ? CHART.slate : SERIES[i % SERIES.length]}
                    />
                  ))}
                </div>
              )}
            </Card>

            <Card title="Predictions" icon={Activity} subtitle="Machine learning forecasts from scikit-learn">
              {fc.loading ? (
                <Loading />
              ) : fc.error ? (
                <ErrorBox message={fc.error} />
              ) : (
                <div className="grid grid-cols-1 gap-3 pt-1 sm:grid-cols-2">
                  <PredictionTile
                    title="Patient Admission Forecast"
                    value={`${fc.data?.headline.next_day ?? 0}`}
                    caption="Predicted admissions (next day)"
                    delta={fc.data?.headline.vs_recent_avg_pct ?? 0}
                    color={CHART.blue}
                    data={(fc.data?.forecast ?? []).map((p) => ({ x: p.label, y: p.predicted }))}
                  />
                  <PredictionTile
                    title="Length of Stay Prediction"
                    value={losDemo.data ? `${losDemo.data.predicted_days} days` : '—'}
                    caption="Typical inpatient (55y, General Medicine)"
                    delta={0}
                    color={CHART.violet}
                    data={(fc.data?.history ?? []).map((p) => ({ x: p.label, y: p.actual }))}
                    hideDelta
                  />
                </div>
              )}
            </Card>
          </div>

          {/* recent encounters */}
          <Card
            title="Recent Patient Encounters"
            icon={ClipboardList}
            action={
              <span className="flex items-center gap-1.5 text-[11.5px] text-ink-mute">
                <CalendarDays size={13} /> latest first
              </span>
            }
            bodyClass="!px-0"
          >
            {recent.loading ? (
              <Loading />
            ) : recent.error ? (
              <div className="px-5"><ErrorBox message={recent.error} /></div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-[12.5px]">
                  <thead>
                    <tr className="text-left text-ink-mute">
                      {['Patient ID', 'Name', 'Encounter Type', 'Visit Date', 'Status', 'Length of Stay'].map((h) => (
                        <th
                          key={h}
                          className="border-b px-5 py-2.5 font-medium"
                          style={{ borderColor: 'var(--c-border)' }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(recent.data?.items ?? []).map((r) => (
                      <tr key={r.ENCOUNTER_ID}>
                        <td className="border-b px-5 py-2.5 font-mono text-[11.5px] text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>
                          {r.PATIENT_ID.slice(0, 8)}
                        </td>
                        <td className="border-b px-5 py-2.5 font-medium text-ink" style={{ borderColor: 'var(--c-border)' }}>
                          {r.FULL_NAME}
                        </td>
                        <td className="border-b px-5 py-2.5 capitalize text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>
                          {r.ENCOUNTERCLASS} · {r.DEPARTMENT}
                        </td>
                        <td className="border-b px-5 py-2.5 tabular-nums text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>
                          {r.VISIT_DATE}
                        </td>
                        <td className="border-b px-5 py-2.5" style={{ borderColor: 'var(--c-border)' }}>
                          <StatusBadge status={r.STATUS} />
                        </td>
                        <td className="border-b px-5 py-2.5 tabular-nums text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>
                          {r.LENGTH_OF_STAY ? `${r.LENGTH_OF_STAY} days` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        {/* ------------------------------------------------ chat rail */}
        <div className="xl:col-span-3">
          <div className="xl:sticky xl:top-[86px] xl:h-[calc(100vh-110px)]">
            <ChatPanel start={start} end={end} compact />
          </div>
        </div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------ small tile */
function PredictionTile({
  title, value, caption, delta, color, data, hideDelta = false,
}: {
  title: string
  value: string
  caption: string
  delta: number
  color: string
  data: { x: string; y: number }[]
  hideDelta?: boolean
}) {
  const up = delta >= 0
  const id = `grad-${title.replace(/\W/g, '')}`
  return (
    <div
      className="rounded-xl2 border p-3.5"
      style={{ borderColor: 'var(--c-border)', backgroundColor: 'var(--c-surface-2)' }}
    >
      <p className="text-[12px] font-medium text-ink-soft">{title}</p>
      <p className="mt-1.5 text-[24px] font-bold leading-none text-ink">{value}</p>
      <p className="mt-1 text-[11px] text-ink-mute">{caption}</p>
      {!hideDelta && (
        <p
          className="mt-1.5 flex items-center gap-1 text-[11.5px] font-semibold"
          style={{ color: up ? 'var(--c-ok)' : 'var(--c-bad)' }}
        >
          {up ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
          {Math.abs(delta).toFixed(1)}%
        </p>
      )}
      <div className="mt-2 h-[52px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                <stop offset="100%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <Area type="monotone" dataKey="y" stroke={color} strokeWidth={1.8} fill={`url(#${id})`} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
