/**
 * One palette for every chart in the app, so the whole dashboard reads as
 * a single system. Values are real hex codes, never inherited from a host
 * page, and each one is legible on both the light and the dark surface.
 */
export const CHART = {
  blue: '#1d6ff2',
  green: '#16a34a',
  violet: '#8b5cf6',
  orange: '#ea8a1e',
  teal: '#0d9488',
  pink: '#ec4899',
  slate: '#94a3b8',
  red: '#e11d48',
}

export const SERIES = [
  CHART.blue,
  CHART.green,
  CHART.violet,
  CHART.orange,
  CHART.teal,
  CHART.pink,
  CHART.red,
  CHART.slate,
]

/** Soft background + strong accent used by the five KPI cards. */
export const KPI_TONES = [
  { bg: '#eaf2fe', bgDark: '#15263f', icon: '#1d6ff2', ring: '#d3e4fd' },
  { bg: '#e8f7ee', bgDark: '#132b20', icon: '#16a34a', ring: '#cfeedc' },
  { bg: '#f1ecfe', bgDark: '#201b38', icon: '#8b5cf6', ring: '#e1d8fb' },
  { bg: '#fdf0e2', bgDark: '#30230f', icon: '#ea8a1e', ring: '#f9dec1' },
  { bg: '#e4f6f3', bgDark: '#0f2b29', icon: '#0d9488', ring: '#c8ebe5' },
]

export function toneFor(i: number) {
  return KPI_TONES[i % KPI_TONES.length]
}
