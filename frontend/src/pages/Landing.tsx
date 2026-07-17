import { resetSessionId } from '../lib/session'

export function Landing({ onStart }: { onStart: () => void }) {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-10 px-6 text-center">
      <div className="space-y-3 max-w-xl">
        <h1 className="text-3xl font-mono font-semibold tracking-wide">
          RED<span style={{ color: 'var(--text-muted)' }}>/</span>BLUE
        </h1>
        <p className="text-[var(--text-muted)]">
          Learn to attack and defend real-world classes of cyberattacks — the OWASP Top
          10 — through scripted, hands-on levels. No real network, no real exploit code.
          Pick a vulnerability, learn how it works, then try both sides.
        </p>
      </div>

      <button
        onClick={onStart}
        className="rounded-lg border-2 px-8 py-4 font-mono text-lg tracking-wide transition-shadow duration-200"
        style={{ borderColor: 'var(--surface-border)', color: 'var(--text)' }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'var(--text-muted)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'var(--surface-border)'
        }}
      >
        START
      </button>

      <button
        onClick={() => {
          resetSessionId()
          onStart()
        }}
        className="font-mono text-xs underline"
        style={{ color: 'var(--text-muted)' }}
      >
        start a fresh session (clears saved progress)
      </button>
    </main>
  )
}
