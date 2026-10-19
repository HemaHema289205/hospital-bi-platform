import { useEffect, useState } from 'react'

export interface Fetched<T> {
  data: T | null
  error: string | null
  loading: boolean
}

/**
 * Tiny data-loading hook: runs `fn` whenever `deps` change, and ignores the
 * result of a request that was superseded while it was still in flight.
 */
export function useFetch<T>(fn: () => Promise<T>, deps: unknown[]): Fetched<T> {
  const [state, setState] = useState<Fetched<T>>({ data: null, error: null, loading: true })

  useEffect(() => {
    let alive = true
    setState((s) => ({ ...s, loading: true, error: null }))
    fn()
      .then((d) => alive && setState({ data: d, error: null, loading: false }))
      .catch((e: Error) => alive && setState({ data: null, error: e.message, loading: false }))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
