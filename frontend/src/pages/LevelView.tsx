import { useEffect, useRef, useState, type FormEvent } from 'react'
import { getLevelDetail, postCommand, type LevelDetail, type VictimPcState } from '../api/client'

type HistoryEntry = { input: string; output: string }

export function LevelView({
  levelId,
  sessionId,
  onBack,
}: {
  levelId: string
  sessionId: string
  onBack: () => void
}) {
  const [level, setLevel] = useState<LevelDetail | null>(null)
  const [state, setState] = useState<VictimPcState | null>(null)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [input, setInput] = useState('')
  const [debrief, setDebrief] = useState<string | null>(null)
  const [hintsShown, setHintsShown] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getLevelDetail(levelId, sessionId).then((detail) => {
      setLevel(detail)
      setState(detail.victim_pc_initial_state)
    })
  }, [levelId, sessionId])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [history])

  if (!level || !state) {
    return <p className="p-10 text-[var(--text-muted)] font-mono">Loading level…</p>
  }

  const accent = level.role === 'red' ? 'var(--red-accent)' : 'var(--blue-accent)'
  const glow = level.role === 'red' ? 'var(--red-glow)' : 'var(--blue-glow)'

  async function runCommand(e: FormEvent) {
    e.preventDefault()
    if (!input.trim()) return
    const result = await postCommand(levelId, sessionId, input)
    setHistory((h) => [...h, { input, output: result.terminal_output }])
    setState(result.victim_pc_state)
    if (result.wins_level) setDebrief(result.debrief)
    setInput('')
  }

  return (
    <main className="min-h-screen px-6 py-6">
      <button
        onClick={onBack}
        className="mb-4 font-mono text-sm rounded border px-3 py-1.5 transition-shadow duration-200"
        style={{ borderColor: 'var(--surface-border)', color: 'var(--text-muted)' }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = accent
          e.currentTarget.style.color = accent
          e.currentTarget.style.boxShadow = `0 0 16px ${glow}`
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'var(--surface-border)'
          e.currentTarget.style.color = 'var(--text-muted)'
          e.currentTarget.style.boxShadow = 'none'
        }}
      >
        ← back to levels
      </button>

      <div className="grid gap-4" style={{ gridTemplateColumns: 'minmax(260px, 25%) 1fr' }}>
        <aside
          className="rounded-lg border p-4 space-y-4 self-start"
          style={{ borderColor: 'var(--surface-border)', background: 'var(--surface)' }}
        >
          <div>
            <span
              className="font-mono text-xs px-2 py-0.5 rounded inline-block"
              style={{ color: accent, border: `1px solid ${accent}` }}
            >
              {level.owasp_category}
            </span>
            <h1 className="text-2xl font-mono font-semibold mt-2">{level.title}</h1>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] mb-1">Objective</p>
            <p className="text-sm">{level.objective}</p>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] mb-1">Briefing</p>
            <p className="text-xs text-[var(--text-muted)]">{level.briefing}</p>
          </div>

          {debrief && (
            <div className="rounded border p-3" style={{ borderColor: 'var(--success)', background: 'var(--surface)' }}>
              <p className="font-mono text-sm mb-2" style={{ color: 'var(--success)' }}>
                ✓ Level complete — what actually happened
              </p>
              <p className="text-xs text-[var(--text-muted)]">{debrief}</p>
            </div>
          )}

          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] mb-2">Hints</p>
            {level.hints.slice(0, hintsShown).map((hint, i) => (
              <p key={i} className="text-sm mb-1">
                {i + 1}. {hint}
              </p>
            ))}
            {hintsShown < level.hints.length && (
              <button
                onClick={() => setHintsShown((n) => n + 1)}
                className="text-xs font-mono underline"
                style={{ color: accent }}
              >
                Show hint {hintsShown + 1} of {level.hints.length}
              </button>
            )}
          </div>
        </aside>

        <div className="space-y-4">
          <div
            ref={scrollRef}
            className="rounded-lg border p-4 font-mono text-sm h-64 overflow-y-auto"
            style={{ borderColor: 'var(--surface-border)', background: 'var(--surface)' }}
          >
            <p className="text-[var(--text-muted)]">connected to victim-pc-01</p>
            {history.map((h, i) => (
              <div key={i} className="mt-2">
                <p style={{ color: accent }}>$ {h.input}</p>
                <p className="whitespace-pre-wrap text-[var(--text)]">{h.output}</p>
              </div>
            ))}
          </div>

          <form onSubmit={runCommand} className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 rounded border px-3 py-2 font-mono text-sm bg-transparent outline-none"
              style={{ borderColor: 'var(--surface-border)', color: 'var(--text)' }}
              placeholder="type a command…"
              autoFocus
            />
            <button
              type="submit"
              className="rounded border px-4 font-mono text-sm transition-shadow duration-200"
              style={{ borderColor: accent, color: accent }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = `0 0 16px ${glow}`
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              run
            </button>
          </form>

          <div
            className="rounded-lg border p-4"
            style={{ borderColor: 'var(--surface-border)', background: 'var(--surface)' }}
          >
            <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] mb-2">Victim PC</p>
            <div className="grid grid-cols-3 gap-4 text-sm font-mono">
              <div>
                <p className="text-[var(--text-muted)] text-xs mb-1">files</p>
                {state.files.map((f) => (
                  <p key={f}>{f}</p>
                ))}
              </div>
              <div>
                <p className="text-[var(--text-muted)] text-xs mb-1">services</p>
                {state.services.map((s) => (
                  <p key={s}>{s}</p>
                ))}
              </div>
              <div>
                <p className="text-[var(--text-muted)] text-xs mb-1">logs</p>
                {state.logs.map((l, i) => (
                  <p key={i} className="text-xs">
                    {l}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
