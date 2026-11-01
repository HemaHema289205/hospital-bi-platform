import { useEffect, useState } from 'react'
import {
  Area, AreaChart, Bar, CartesianGrid, ComposedChart, Legend, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Brain, Gauge, Sparkles } from 'lucide-react'
import type { RangeCtx } from '../App'
import { api } from '../api'
import { useFetch } from '../lib/useFetch'
import { Card, ErrorBox, Loading } from '../components/ui'
import { CHART } from '../lib/colors'
import type { LosResponse } from '../types'

export default function Predictions({ ctx }: { ctx: RangeCtx }) {
  const [horizon, setHorizon] = useState(7)
  const fc = useFetch(() => api.forecast(horizon), [horizon])
  const metrics = useFetch(() => api.modelMetrics(), [])
  const options = useFetch(() => api.predictionOptions(), [])

  const [form, setForm] = useState({
    age: 62,
    gender: 'Male',
    department: 'General Medicine',
    encounter_class: 'inpatient',
    wait_minutes: 30,
  })
  const [los, setLos] = useState<LosResponse | null>(null)
  const [losErr, setLosErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (options.data?.DEPARTMENT?.length) {
      setForm((f) => ({ ...f, department: options.data!.DEPARTMENT[0] }))
    }
  }, [options.data])

  async function runPrediction() {
    setBusy(true)
    setLosErr(null)
    try {
      setLos(await api.predictLos(form))
    } catch (e) {
      setLosErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const axis = { fontSize: 11, fill: 'var(--c-ink-mute)' }

  // History and forecast are stitched into one continuous chart. The last
  // real day also carries a `predicted` value, otherwise the dashed forecast
  // line would float disconnected from the solid history line.
  const history = fc.data?.history ?? []
  const combined = [
    ...history.map((h, i) => ({
      label: h.label,
      actual: h.actual,
      ...(i === history.length - 1 ? { predicted: h.actual } : {}),
    })),
    ...(fc.data?.forecast ?? []).map((f) => ({
      label: f.label,
      predicted: f.predicted,
      band: [f.lower, f.upper] as [number, number],
    })),
  ]

  const RISK: Record<string, string> = {
    Low: 'var(--c-ok)', Medium: 'var(--c-warn)', High: 'var(--c-bad)',
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-[24px] font-bold tracking-tight text-ink">ML Predictions</h1>
        <p className="mt-0.5 text-[13px] text-ink-soft">
          scikit-learn models trained on the hospital's own history
        </p>
      </div>

      {/* forecast */}
      <Card
        title="Patient Admission Forecast"
        subtitle={fc.data ? `Model in use: ${fc.data.model}` : undefined}
        action={
          <select
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
            aria-label="Forecast horizon"
            className="!w-auto !py-1.5 text-[12.5px]"
          >
            {[7, 14, 21, 30].map((d) => <option key={d} value={d}>Next {d} days</option>)}
          </select>
        }
      >
        {fc.loading ? <Loading /> : fc.error ? <ErrorBox message={fc.error} /> : (
          <>
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Next day" value={`${fc.data?.headline.next_day}`} hint={fc.data?.headline.confidence} icon={<Sparkles size={15} />} />
              <Stat label="30-day average" value={`${fc.data?.headline.recent_avg}`} hint="admissions / day" icon={<Gauge size={15} />} />
              <Stat label="Model MAE" value={`${fc.data?.metrics?.mae}`} hint="avg error, admissions" icon={<Brain size={15} />} />
              <Stat label="Model R²" value={`${fc.data?.metrics?.r2}`} hint="on unseen days" icon={<Brain size={15} />} />
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={combined} margin={{ top: 8, right: 10, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="var(--c-grid)" vertical={false} />
                <XAxis dataKey="label" tick={axis} tickLine={false} axisLine={false} minTickGap={20} />
                <YAxis tick={axis} tickLine={false} axisLine={false} width={52} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 11.5 }} />
                <Area dataKey="band" name="Confidence range" stroke="none" fill={CHART.violet} fillOpacity={0.14} />
                <Line type="monotone" dataKey="actual" name="Actual (history)" stroke={CHART.blue} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="predicted" name="Predicted" stroke={CHART.violet} strokeWidth={2} strokeDasharray="5 4" dot={{ r: 2.5 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* LOS predictor */}
        <Card title="Length of Stay Predictor" subtitle="Enter a patient's details to estimate how long they will stay">
          <div className="grid grid-cols-2 gap-3 pt-1">
            <Field label="Age">
              <input
                type="number" min={0} max={110} value={form.age}
                onChange={(e) => setForm({ ...form, age: Number(e.target.value) })}
              />
            </Field>
            <Field label="Gender">
              <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                {(options.data?.GENDER_LABEL ?? ['Male', 'Female']).map((g) => <option key={g}>{g}</option>)}
              </select>
            </Field>
            <Field label="Department">
              <select value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>
                {(options.data?.DEPARTMENT ?? ['General Medicine']).map((d) => <option key={d}>{d}</option>)}
              </select>
            </Field>
            <Field label="Admission type">
              <select value={form.encounter_class} onChange={(e) => setForm({ ...form, encounter_class: e.target.value })}>
                {ADMISSION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </Field>
            <Field label="Waiting time (minutes)">
              <input
                type="number" min={0} max={600} value={form.wait_minutes}
                onChange={(e) => setForm({ ...form, wait_minutes: Number(e.target.value) })}
              />
            </Field>
            <div className="flex items-end">
              <button onClick={runPrediction} disabled={busy} className="btn-primary w-full !py-2.5">
                {busy ? 'Predicting…' : 'Predict stay'}
              </button>
            </div>
          </div>

          {losErr && <div className="mt-4"><ErrorBox message={losErr} /></div>}

          {los && (
            <div
              className="mt-4 rounded-xl2 border p-4"
              style={{ borderColor: 'var(--c-border)', backgroundColor: 'var(--c-surface-2)' }}
            >
              <div className="flex items-end justify-between gap-3">
                <div>
                  {los.predicted_hours != null ? (
                    <>
                      <p className="text-[12px] text-ink-soft">Expected time in hospital (OP visit)</p>
                      <p className="mt-1 text-[32px] font-bold leading-none text-ink">
                        {los.predicted_hours} <span className="text-[16px] font-semibold text-ink-soft">hours</span>
                      </p>
                      <p className="mt-1.5 text-[11.5px] text-ink-mute">
                        likely range {los.hours_low} – {los.hours_high} hours · same day, no bed
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="text-[12px] text-ink-soft">Predicted length of stay</p>
                      <p className="mt-1 text-[32px] font-bold leading-none text-ink">
                        {los.predicted_days} <span className="text-[16px] font-semibold text-ink-soft">days</span>
                      </p>
                      <p className="mt-1.5 text-[11.5px] text-ink-mute">
                        likely range {los.range_low} – {los.range_high} days
                      </p>
                    </>
                  )}
                </div>
                <span
                  className="chip"
                  style={{ backgroundColor: 'var(--c-brand-soft)', color: RISK[los.risk_level] }}
                >
                  {los.risk_level} risk
                </span>
              </div>
              <p className="mt-3 border-t pt-3 text-[12.5px] text-ink-soft" style={{ borderColor: 'var(--c-border)' }}>
                {los.recommendation}
              </p>
            </div>
          )}
        </Card>

        {/* model report card */}
        <Card title="Model Performance" subtitle="How the models scored on data they had never seen">
          {metrics.loading ? <Loading /> : metrics.error ? <ErrorBox message={metrics.error} /> : (
            <div className="space-y-4 pt-1">
              {Object.entries(metrics.data ?? {}).map(([key, m]: [string, any]) => (
                <div
                  key={key}
                  className="rounded-xl2 border p-3.5"
                  style={{ borderColor: 'var(--c-border)', backgroundColor: 'var(--c-surface-2)' }}
                >
                  <p className="text-[13px] font-semibold capitalize text-ink">
                    {key.replace(/_/g, ' ')}
                  </p>
                  <p className="mt-0.5 text-[11.5px] text-ink-mute">{m.model} → {m.target}</p>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                    {[
                      { k: 'MAE', v: m.mae },
                      { k: 'RMSE', v: m.rmse },
                      { k: 'R²', v: m.r2 },
                    ].map((s) => (
                      <div key={s.k} className="rounded-[10px] py-2" style={{ backgroundColor: 'var(--c-surface)' }}>
                        <p className="text-[15px] font-bold tabular-nums text-ink">{s.v}</p>
                        <p className="text-[10.5px] text-ink-mute">{s.k}</p>
                      </div>
                    ))}
                  </div>
                  {m.all_models && (
                    <table className="mt-3 w-full text-[11.5px]">
                      <thead>
                        <tr className="text-left text-ink-mute">
                          <th className="py-1 font-medium">Candidate</th>
                          <th className="py-1 font-medium">MAE</th>
                          <th className="py-1 font-medium">R²</th>
                        </tr>
                      </thead>
                      <tbody>
                        {m.all_models.map((c: any) => (
                          <tr key={c.name} className={c.name === m.model ? 'font-semibold text-ink' : 'text-ink-soft'}>
                            <td className="py-0.5">{c.name}{c.name === m.model ? '  ✓' : ''}</td>
                            <td className="py-0.5 tabular-nums">{c.mae}</td>
                            <td className="py-0.5 tabular-nums">{c.r2}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

function Stat({ label, value, hint, icon }: { label: string; value: string; hint?: string; icon: React.ReactNode }) {
  return (
    <div
      className="rounded-xl2 border p-3"
      style={{ borderColor: 'var(--c-border)', backgroundColor: 'var(--c-surface-2)' }}
    >
      <p className="flex items-center gap-1.5 text-[11.5px] text-ink-mute">
        <span style={{ color: 'var(--c-brand)' }}>{icon}</span>
        {label}
      </p>
      <p className="mt-1 text-[22px] font-bold leading-none text-ink">{value}</p>
      {hint && <p className="mt-1 text-[11px] text-ink-mute">{hint}</p>}
    </div>
  )
}

/**
 * Visit types the predictor accepts. Outpatient (OP) is never admitted, so the
 * backend answers 0 days for it; the others go to the length-of-stay model.
 */
const ADMISSION_TYPES = [
  { value: 'inpatient', label: 'Inpatient (IP)' },
  { value: 'outpatient', label: 'Outpatient (OP)' },
  { value: 'emergency', label: 'Emergency' },
  { value: 'urgentcare', label: 'Urgent care' },
]

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11.5px] font-medium text-ink-soft">{label}</span>
      {children}
    </label>
  )
}
