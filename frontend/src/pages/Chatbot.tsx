import { useSearchParams } from 'react-router-dom'
import { Database, MessageSquare, Sparkles } from 'lucide-react'
import type { RangeCtx } from '../App'
import { ChatPanel } from '../components/ChatPanel'
import { Card } from '../components/ui'
import { DateRange } from '../components/DateRange'

const EXAMPLES = [
  'How many patients were admitted this month?',
  'What is the average length of stay?',
  'Which department is busiest?',
  'What is the bed occupancy right now?',
  'Show me the top medical conditions',
  'Predict admissions for the next 7 days',
  'Predict length of stay for a 70 year old emergency patient',
  'Give me a summary',
]

export default function Chatbot({ ctx }: { ctx: RangeCtx }) {
  const { start, end, days, setDays } = ctx
  const [params] = useSearchParams()
  const initial = params.get('q') ?? undefined

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[24px] font-bold tracking-tight text-ink">AI Chatbot</h1>
          <p className="mt-0.5 text-[13px] text-ink-soft">
            Ask questions in plain English. Every number comes straight from the database.
          </p>
        </div>
        <DateRange start={start} end={end} days={days} onChangeDays={setDays} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="h-[640px]">
            <ChatPanel start={start} end={end} initialQuestion={initial} />
          </div>
        </div>

        <div className="space-y-4">
          <Card title="Try asking">
            <ul className="space-y-2 pt-1">
              {EXAMPLES.map((q) => (
                <li
                  key={q}
                  className="flex items-start gap-2 text-[12.5px] text-ink-soft"
                >
                  <MessageSquare size={13} className="mt-0.5 shrink-0" style={{ color: 'var(--c-brand)' }} />
                  {q}
                </li>
              ))}
            </ul>
          </Card>

          <Card title="How it works">
            <div className="space-y-3 pt-1 text-[12.5px] text-ink-soft">
              <Step icon={<MessageSquare size={14} />} title="1. Understand">
                Your question is matched to an intent (admissions, stay length, forecast, and so on).
              </Step>
              <Step icon={<Database size={14} />} title="2. Query">
                The matching SQL runs against the hospital database — never a guessed number.
              </Step>
              <Step icon={<Sparkles size={14} />} title="3. Answer">
                The result is written back in plain English. Switch{' '}
                <code className="font-mono">LLM_PROVIDER</code> in <code className="font-mono">.env</code>{' '}
                to <code className="font-mono">ollama</code> or <code className="font-mono">openai</code>{' '}
                to have a language model phrase the answer instead.
              </Step>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

function Step({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2.5">
      <span
        className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full"
        style={{ backgroundColor: 'var(--c-brand-soft)', color: 'var(--c-brand)' }}
      >
        {icon}
      </span>
      <p>
        <span className="font-semibold text-ink">{title}</span> — {children}
      </p>
    </div>
  )
}
