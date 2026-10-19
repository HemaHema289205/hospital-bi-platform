import { useEffect, useRef, useState } from 'react'
import { Bot, Send } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../lib/auth'
import type { ChatResponse } from '../types'

export interface Msg {
  id: number
  role: 'user' | 'bot'
  text: string
  time: string
  provider?: string
}

const now = () =>
  new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })

/** Renders **bold** and line breaks without pulling in a markdown library. */
function RichText({ text }: { text: string }) {
  return (
    <>
      {text.split('\n').map((line, i) => (
        <span key={i} className="block">
          {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
            part.startsWith('**') && part.endsWith('**') ? (
              <strong key={j} className="font-semibold">{part.slice(2, -2)}</strong>
            ) : (
              <span key={j}>{part}</span>
            ),
          )}
        </span>
      ))}
    </>
  )
}

export function ChatPanel({
  start, end, compact = false, initialQuestion,
}: {
  start: string
  end: string
  compact?: boolean
  initialQuestion?: string
}) {
  const { user } = useAuth()
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: 0,
      role: 'bot',
      text: `Hello ${user?.name ?? 'there'}. Ask me anything about patient flow, admissions, departments or predictions.`,
      time: now(),
    },
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([
    'Show patient flow trends',
    'What is the average length of stay?',
    'Predict admissions for the next 7 days',
  ])
  const endRef = useRef<HTMLDivElement>(null)
  const askedRef = useRef(false)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy])

  useEffect(() => {
    if (initialQuestion && !askedRef.current) {
      askedRef.current = true
      void send(initialQuestion)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuestion])

  async function send(text: string) {
    const question = text.trim()
    if (!question || busy) return
    setInput('')
    setMessages((m) => [...m, { id: Date.now(), role: 'user', text: question, time: now() }])
    setBusy(true)
    try {
      const res: ChatResponse = await api.chat(question, start, end)
      setMessages((m) => [...m, {
        id: Date.now() + 1, role: 'bot', text: res.reply, time: now(), provider: res.provider,
      }])
      if (res.suggestions?.length) setSuggestions(res.suggestions.slice(0, 3))
    } catch (err) {
      setMessages((m) => [...m, {
        id: Date.now() + 1,
        role: 'bot',
        time: now(),
        text: `I could not reach the backend. ${(err as Error).message}`,
      }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card flex h-full min-h-0 flex-col">
      <header
        className="flex items-center gap-2.5 border-b px-4 py-3.5"
        style={{ borderColor: 'var(--c-border)' }}
      >
        <div
          className="grid h-8 w-8 place-items-center rounded-full"
          style={{ backgroundColor: 'var(--c-brand-soft)' }}
        >
          <Bot size={17} style={{ color: 'var(--c-brand)' }} />
        </div>
        <h2 className="card-title flex-1">AI Assistant</h2>
        <span className="flex items-center gap-1.5 text-[11.5px] text-ink-mute">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: 'var(--c-ok)' }}
          />
          Online
        </span>
      </header>

      <div
        className={`flex-1 space-y-3 overflow-y-auto px-4 py-4 ${compact ? 'max-h-[420px]' : ''}`}
      >
        {messages.map((m) => (
          <div key={m.id} className={m.role === 'user' ? 'flex justify-end' : 'flex gap-2'}>
            {m.role === 'bot' && (
              <div
                className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full"
                style={{ backgroundColor: 'var(--c-brand-soft)' }}
              >
                <Bot size={14} style={{ color: 'var(--c-brand)' }} />
              </div>
            )}
            <div className={m.role === 'user' ? 'max-w-[85%]' : 'max-w-[88%]'}>
              <div
                className="rounded-[13px] px-3.5 py-2.5 text-[12.8px] leading-relaxed"
                style={
                  m.role === 'user'
                    ? { backgroundColor: 'var(--c-brand)', color: '#ffffff' }
                    : { backgroundColor: 'var(--c-surface-2)', color: 'var(--c-ink)' }
                }
              >
                <RichText text={m.text} />
              </div>
              <p
                className={`mt-1 text-[10.5px] text-ink-mute ${m.role === 'user' ? 'text-right' : ''}`}
              >
                {m.time}
              </p>
            </div>
          </div>
        ))}

        {busy && (
          <div className="flex gap-2">
            <div
              className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full"
              style={{ backgroundColor: 'var(--c-brand-soft)' }}
            >
              <Bot size={14} style={{ color: 'var(--c-brand)' }} />
            </div>
            <div
              className="flex items-center gap-1 rounded-[13px] px-4 py-3"
              style={{ backgroundColor: 'var(--c-surface-2)' }}
            >
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="inline-block h-1.5 w-1.5 animate-bounce rounded-full"
                  style={{ backgroundColor: 'var(--c-ink-mute)', animationDelay: `${i * 120}ms` }}
                />
              ))}
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="space-y-2 px-4 pb-4">
        <div className="flex flex-wrap gap-1.5">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => void send(s)}
              disabled={busy}
              className="rounded-full border px-3 py-1.5 text-[11.5px] transition-colors"
              style={{
                borderColor: 'var(--c-border)',
                color: 'var(--c-ink-soft)',
                backgroundColor: 'var(--c-surface-2)',
              }}
            >
              {s}
            </button>
          ))}
        </div>

        <form
          onSubmit={(e) => { e.preventDefault(); void send(input) }}
          className="flex items-center gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your question…"
            aria-label="Ask the AI assistant"
            disabled={busy}
          />
          <button
            type="submit"
            className="btn-primary h-[38px] w-[42px] !px-0"
            disabled={busy || !input.trim()}
            aria-label="Send message"
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  )
}
