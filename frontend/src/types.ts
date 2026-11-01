export interface KpiCardData {
  key: string
  label: string
  format: 'number' | 'currency' | 'days'
  value: number
  change_pct: number
  previous: number
}

export interface KpiResponse {
  range: { start: string; end: string }
  previous_range: { start: string; end: string }
  cards: KpiCardData[]
  extra: {
    emergency_cases: number
    avg_wait_minutes: number
    unique_patients: number
  }
}

export interface FlowPoint {
  date: string
  label: string
  visits: number
  admissions: number
  discharges: number
  emergency: number
  occupancy: number
  wait_minutes: number
}

export interface NameValue {
  name: string
  value: number
  pct: number
  admissions?: number
}

export interface Demographics {
  total: number
  gender: NameValue[]
  /** Men and Women are adults (18+), Children are under 18 */
  groups: NameValue[]
  age_bands: NameValue[]
}

export interface Department {
  name: string
  visits: number
  admissions: number
  emergency: number
  avg_los: number
  avg_wait: number
  revenue: number
  pct: number
  men: number
  women: number
  children: number
}

export interface Ward {
  ward: string
  beds: number
  occupied: number
  available: number
  occupancy_pct: number
}

export interface WaitTime {
  name: string
  label: string
  avg_wait: number
  max_wait: number
  visits: number
}

export interface WeekdayPoint {
  dow: number
  day: string
  day_short: string
  visits: number
  admissions: number
  wait_minutes: number
}

export interface HourPoint {
  hour: number
  visits: number
  emergency: number
}

export interface EncounterRow {
  ENCOUNTER_ID: string
  PATIENT_ID: string
  FULL_NAME: string
  AGE: number
  GENDER_LABEL: string
  DEPARTMENT: string
  ENCOUNTERCLASS: string
  VISIT_DATE: string
  STATUS: string
  LENGTH_OF_STAY: number | null
  WAIT_MINUTES: number
}

export interface ForecastPoint {
  date: string
  label: string
  day: string
  predicted: number
  lower: number
  upper: number
}

export interface ForecastResponse {
  model: string
  metrics: Record<string, any>
  history: { date: string; label: string; actual: number }[]
  forecast: ForecastPoint[]
  headline: {
    next_day: number
    confidence: string
    vs_recent_avg_pct: number
    recent_avg: number
  }
}

export interface LosResponse {
  predicted_days: number
  range_low: number
  range_high: number
  /** set only for outpatient visits, which are measured in hours, not days */
  predicted_hours?: number
  hours_low?: number
  hours_high?: number
  risk_level: string
  recommendation: string
  model: string
  model_mae: number
}

export interface ChatResponse {
  reply: string
  intent: string
  provider: string
  context: { chart: string; data: any } | null
  suggestions: string[]
}

export interface MetaResponse {
  data_range: { min_date: string; max_date: string }
  default_range: { start: string; end: string }
  departments: string[]
  total_beds: number
  models_trained: boolean
}

export interface ReportResult {
  columns: string[]
  rows: Record<string, any>[]
  row_count: number
}
