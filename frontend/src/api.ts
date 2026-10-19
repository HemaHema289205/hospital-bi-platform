/**
 * Every call to the FastAPI backend lives here.
 * In development Vite proxies /api -> http://127.0.0.1:8000 (vite.config.ts).
 */
import type {
  ChatResponse, Demographics, Department, EncounterRow, FlowPoint,
  ForecastResponse, HourPoint, KpiResponse, LosResponse, MetaResponse,
  NameValue, ReportResult, Ward, WaitTime, WeekdayPoint,
} from './types'

const BASE = import.meta.env.VITE_API_BASE ?? ''

/** The session token, kept here so every request can carry it. */
let authToken: string | null = null

export function setAuthToken(token: string | null): void {
  authToken = token
}

function headers(extra: Record<string, string> = {}): Record<string, string> {
  return authToken ? { ...extra, Authorization: `Bearer ${authToken}` } : extra
}

/**
 * Called when the server rejects the session (expired or invalid token), so
 * the app can drop straight back to the login screen instead of showing an
 * error on every card.
 */
let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(fn: (() => void) | null): void {
  onUnauthorized = fn
}

function checkAuth(path: string, status: number): void {
  if (status === 401 && !path.startsWith('/api/auth/')) onUnauthorized?.()
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: headers() })
  if (!res.ok) {
    checkAuth(path, res.status)
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

async function post<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: headers({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    checkAuth(path, res.status)
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

const range = (s: string, e: string) => `start=${s}&end=${e}`

export interface LoginResponse {
  token: string
  expires_in_hours: number
  user: { username: string; name: string; role: string }
}

export const api = {
  login: (username: string, password: string) =>
    post<LoginResponse>('/api/auth/login', { username, password }),
  me: () => get<{ username: string; name: string; role: string }>('/api/auth/me'),
  demoAccounts: () =>
    get<{ items: { username: string; password: string; role: string }[] }>(
      '/api/auth/demo-accounts',
    ),

  health: () => get<Record<string, unknown>>('/api/health'),
  meta: () => get<MetaResponse>('/api/meta'),

  kpis: (s: string, e: string) => get<KpiResponse>(`/api/kpis?${range(s, e)}`),
  patientFlow: (s: string, e: string) =>
    get<{ series: FlowPoint[] }>(`/api/patient-flow?${range(s, e)}`),
  demographics: (s: string, e: string) => get<Demographics>(`/api/demographics?${range(s, e)}`),
  conditions: (s: string, e: string, limit = 5) =>
    get<{ items: NameValue[] }>(`/api/conditions?${range(s, e)}&limit=${limit}`),
  recent: (limit = 10) => get<{ items: EncounterRow[] }>(`/api/encounters/recent?limit=${limit}`),

  departments: (s: string, e: string) =>
    get<{ items: Department[] }>(`/api/departments?${range(s, e)}`),
  bedOccupancy: (s: string, e: string) => get<{ items: Ward[] }>(`/api/bed-occupancy?${range(s, e)}`),
  waitTimes: (s: string, e: string) => get<{ items: WaitTime[] }>(`/api/wait-times?${range(s, e)}`),
  hourlyFlow: (s: string, e: string) => get<{ items: HourPoint[] }>(`/api/hourly-flow?${range(s, e)}`),
  weekdayFlow: (s: string, e: string) =>
    get<{ items: WeekdayPoint[] }>(`/api/weekday-flow?${range(s, e)}`),

  forecast: (days = 7) => get<ForecastResponse>(`/api/predictions/admissions?days=${days}`),
  predictLos: (payload: {
    age: number; gender: string; department: string
    encounter_class: string; wait_minutes: number
  }) => post<LosResponse>('/api/predictions/length-of-stay', payload),
  predictionOptions: () => get<Record<string, string[]>>('/api/predictions/options'),
  modelMetrics: () => get<Record<string, any>>('/api/model-metrics'),

  search: (q: string) => get<{ items: EncounterRow[] }>(`/api/search?q=${encodeURIComponent(q)}`),
  sampleQueries: () => get<{ items: { title: string; sql: string }[] }>('/api/reports/samples'),
  runQuery: (sql: string) => post<ReportResult>('/api/reports/query', { sql, limit: 200 }),

  chat: (message: string, start?: string, end?: string) =>
    post<ChatResponse>('/api/chat', { message, start, end }),
}
