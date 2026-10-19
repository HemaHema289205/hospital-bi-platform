/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      // Every colour comes from a CSS variable defined in src/index.css,
      // where light and dark themes are both written out with real hex values.
      colors: {
        app: 'var(--c-app)',
        surface: 'var(--c-surface)',
        'surface-2': 'var(--c-surface-2)',
        border: 'var(--c-border)',
        ink: 'var(--c-ink)',
        'ink-soft': 'var(--c-ink-soft)',
        'ink-mute': 'var(--c-ink-mute)',
        brand: 'var(--c-brand)',
        'brand-dark': 'var(--c-brand-dark)',
        'brand-soft': 'var(--c-brand-soft)',
        nav: 'var(--c-nav)',
        'nav-soft': 'var(--c-nav-soft)',
        'nav-ink': 'var(--c-nav-ink)',
        'nav-mute': 'var(--c-nav-mute)',
        ok: 'var(--c-ok)',
        warn: 'var(--c-warn)',
        bad: 'var(--c-bad)',
        violet: 'var(--c-violet)',
        teal: 'var(--c-teal)',
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'Liberation Mono', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px 0 rgba(15, 23, 42, 0.04), 0 1px 3px 0 rgba(15, 23, 42, 0.06)',
        pop: '0 10px 30px -12px rgba(15, 23, 42, 0.25)',
      },
      borderRadius: { xl2: '14px' },
    },
  },
  plugins: [],
}
