import { useState } from 'react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { RangeCtx } from '../App'
import { api } from '../api'
import { useFetch } from '../lib/useFetch'
import { Card, ErrorBox, Loading, MeterRow } from '../components/ui'
import { DateRange } from '../components/DateRange'
import { CHART, SERIES } from '../lib/colors'
import { fmtMoney, fmtNumber } from '../lib/format'

export default function PatientFlow({ ctx }: { ctx: RangeCtx }) {
  const { start, end } = ctx

  const flow = useFetch(() => api.patientFlow(start, end), [start, end])
  const depts = useFetch(() => api.departments(start, end), [start, end])
  const beds = useFetch(() => api.bedOccupancy(start, end), [start, end])
  const waits = useFetch(() => api.waitTimes(start, end), [start, end])
  const weekday = useFetch(() => api.weekdayFlow(start, end), [start, end])

  // department picked in the pie; falls back to the busiest one
  const [picked, setPicked] = useState<string | null>(null)
  const deptItems = depts.data?.items ?? []
  const selected = deptItems.find((d) => d.name === picked) ?? deptItems[0]
  const hourly = useFetch(() => api.hourlyFlow(start, end), [start, end])

  const axis = { fontSize: 11, fill: 'var(--c-ink-mute)' }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[24px] font-bold tracking-tight text-ink">Patient Flow Analytics</h1>
          <p className="mt-0.5 text-[13px] text-ink-soft">
            How patients move through the hospital: departments, beds, waiting times and peak hours
          </p>
        </div>
        <DateRange ctx={ctx} />
      </div>

      {/* occupancy over time */}
      <Card title="Bed Occupancy Over Time" subtitle="Share of the hospital's beds in use each day">
        {flow.loading ? <Loading /> : flow.error ? <ErrorBox message={flow.error} /> : (
          <ResponsiveContainer width="100%" height={230}>
            <AreaChart data={flow.data?.series ?? []} margin={{ top: 8, right: 10, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="occ" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART.blue} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={CHART.blue} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--c-grid)" vertical={false} />
              <XAxis dataKey="label" tick={axis} tickLine={false} axisLine={false} minTickGap={24} />
              <YAxis tick={axis} tickLine={false} axisLine={false} width={52} unit="%" domain={[0, 100]} />
              <Tooltip formatter={(v: number) => [`${v}%`, 'Occupancy']} />
              <Area type="monotone" dataKey="occupancy" stroke={CHART.blue} strokeWidth={2} fill="url(#occ)"
                dot={(flow.data?.series.length ?? 0) <= 3} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* department share: click a slice or a name to see who that department treats */}
        <Card title="Department-wise Patient Flow" subtitle="Click a department to see men, women and children">
          {depts.loading ? <Loading /> : depts.error ? <ErrorBox message={depts.error} /> : (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
              <div className="h-[200px] w-full shrink-0 sm:w-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={deptItems}
                      dataKey="visits"
                      nameKey="name"
                      innerRadius={50}
                      outerRadius={88}
                      paddingAngle={2}
                      stroke="none"
                      onClick={(d: { name: string }) => setPicked(d.name)}
                      className="cursor-pointer"
                    >
                      {deptItems.map((d, i) => (
                        <Cell
                          key={d.name}
                          fill={SERIES[i % SERIES.length]}
                          fillOpacity={selected && d.name !== selected.name ? 0.35 : 1}
                        />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number, n: string) => [`${fmtNumber(v)} visits`, n]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="min-w-0 flex-1 space-y-3">
                <div className="flex flex-wrap gap-1.5">
                  {deptItems.map((d, i) => (
                    <button
                      key={d.name}
                      type="button"
                      onClick={() => setPicked(d.name)}
                      className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11.5px] transition-colors"
                      style={{
                        borderColor: d.name === selected?.name ? SERIES[i % SERIES.length] : 'var(--c-border)',
                        backgroundColor: d.name === selected?.name ? 'var(--c-surface-2)' : 'transparent',
                        color: d.name === selected?.name ? 'var(--c-ink)' : 'var(--c-ink-soft)',
                      }}
                    >
                      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: SERIES[i % SERIES.length] }} />
                      {d.name}
                    </button>
                  ))}
                </div>

                {selected && (
                  <div className="rounded-xl2 border p-3" style={{ borderColor: 'var(--c-border)', backgroundColor: 'var(--c-surface-2)' }}>
                    <div className="mb-2.5 flex items-baseline justify-between gap-2">
                      <p className="text-[14px] font-semibold text-ink">{selected.name}</p>
                      <p className="text-[12px] text-ink-soft">
                        <span className="font-semibold text-ink">{fmtNumber(selected.visits)}</span> visits · {selected.pct}% of all
                      </p>
                    </div>
                    <div className="space-y-2">
                      {[
                        { label: 'Men', value: selected.men, color: CHART.blue },
                        { label: 'Women', value: selected.women, color: CHART.pink },
                        { label: 'Children', value: selected.children, color: CHART.orange },
                      ].map((g) => (
                        <MeterRow
                          key={g.label}
                          label={`${g.label}: ${fmtNumber(g.value)}`}
                          pct={(g.value / (selected.visits || 1)) * 100}
                          value={`${((g.value / (selected.visits || 1)) * 100).toFixed(1)}%`}
                          color={g.color}
                        />
                      ))}
                    </div>
                    <p className="mt-2 text-[11px] text-ink-mute">Children: under 18 · Men, Women: 18+</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </Card>

        {/* bed occupancy per ward */}
        <Card title="Bed Occupancy & Utilisation" subtitle="Beds in use on the last day of the period">
          {beds.loading ? <Loading /> : beds.error ? <ErrorBox message={beds.error} /> : (
            <div className="space-y-3 pt-2">
              {(beds.data?.items ?? []).map((w, i) => (
                <MeterRow
                  key={w.ward}
                  label={`${w.ward} (${w.occupied}/${w.beds})`}
                  pct={w.occupancy_pct}
                  value={`${w.occupancy_pct}%`}
                  color={w.occupancy_pct > 90 ? CHART.red : w.occupancy_pct > 75 ? CHART.orange : SERIES[i % SERIES.length]}
                />
              ))}
            </div>
          )}
        </Card>

        {/* waiting times */}
        <Card title="Waiting Time Analysis" subtitle="Average minutes before treatment starts">
          {waits.loading ? <Loading /> : waits.error ? <ErrorBox message={waits.error} /> : (
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={waits.data?.items ?? []} margin={{ top: 8, right: 10, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="var(--c-grid)" vertical={false} />
                <XAxis dataKey="label" tick={axis} tickLine={false} axisLine={false} />
                <YAxis tick={axis} tickLine={false} axisLine={false} width={52} unit="m" />
                <Tooltip formatter={(v: number) => [`${v} min`, 'Average wait']} cursor={{ fill: 'var(--c-grid)' }} />
                <Bar dataKey="avg_wait" radius={[6, 6, 0, 0]}>
                  {(waits.data?.items ?? []).map((_, i) => (
                    <Cell key={i} fill={SERIES[i % SERIES.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* weekday pattern */}
        <Card title="Visits by Day of Week" subtitle="Where the weekly peaks fall">
          {weekday.loading ? <Loading /> : weekday.error ? <ErrorBox message={weekday.error} /> : (
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={weekday.data?.items ?? []} margin={{ top: 8, right: 10, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="var(--c-grid)" vertical={false} />
                <XAxis dataKey="day_short" tick={axis} tickLine={false} axisLine={false} />
                <YAxis tick={axis} tickLine={false} axisLine={false} width={52} />
                <Tooltip cursor={{ fill: 'var(--c-grid)' }} />
                <Legend wrapperStyle={{ fontSize: 11.5 }} />
                <Bar dataKey="visits" name="Visits" fill={CHART.blue} radius={[6, 6, 0, 0]} />
                <Bar dataKey="admissions" name="Admissions" fill={CHART.green} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* hourly */}
      <Card title="Arrivals by Hour of Day" subtitle="Staffing peaks across a 24-hour clock">
        {hourly.loading ? <Loading /> : hourly.error ? <ErrorBox message={hourly.error} /> : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={hourly.data?.items ?? []} margin={{ top: 8, right: 10, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--c-grid)" vertical={false} />
              <XAxis dataKey="hour" tick={axis} tickLine={false} axisLine={false}
                tickFormatter={(h: number) => `${String(h).padStart(2, '0')}:00`} minTickGap={8} />
              <YAxis tick={axis} tickLine={false} axisLine={false} width={52} />
              <Tooltip cursor={{ fill: 'var(--c-grid)' }}
                labelFormatter={(h) => `${String(h).padStart(2, '0')}:00`} />
              <Legend wrapperStyle={{ fontSize: 11.5 }} />
              <Bar dataKey="visits" name="All visits" fill={CHART.blue} radius={[5, 5, 0, 0]} />
              <Bar dataKey="emergency" name="Emergency" fill={CHART.red} radius={[5, 5, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      {/* department table */}
      <Card title="Department Performance" bodyClass="!px-0">
        {depts.loading ? <Loading /> : depts.error ? <div className="px-5"><ErrorBox message={depts.error} /></div> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-[12.5px]">
              <thead>
                <tr className="text-left text-ink-mute">
                  {['Department', 'Visits', 'Admissions', 'Emergency', 'Avg LOS', 'Avg Wait', 'Revenue', 'Share'].map((h) => (
                    <th key={h} className="border-b px-5 py-2.5 font-medium" style={{ borderColor: 'var(--c-border)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(depts.data?.items ?? []).map((d) => (
                  <tr key={d.name}>
                    <td className="border-b px-5 py-2.5 font-medium text-ink" style={{ borderColor: 'var(--c-border)' }}>{d.name}</td>
                    <td className="border-b px-5 py-2.5 tabular-nums text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>{fmtNumber(d.visits)}</td>
                    <td className="border-b px-5 py-2.5 tabular-nums text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>{fmtNumber(d.admissions)}</td>
                    <td className="border-b px-5 py-2.5 tabular-nums text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>{fmtNumber(d.emergency)}</td>
                    <td className="border-b px-5 py-2.5 tabular-nums text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>{d.avg_los} d</td>
                    <td className="border-b px-5 py-2.5 tabular-nums text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>{d.avg_wait} m</td>
                    <td className="border-b px-5 py-2.5 tabular-nums text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>{fmtMoney(d.revenue)}</td>
                    <td className="border-b px-5 py-2.5 tabular-nums text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>{d.pct}%</td>
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
