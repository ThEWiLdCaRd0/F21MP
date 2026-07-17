import { useEffect, useState } from 'react'
import { getVulnerabilities, type VulnerabilityEntry } from '../api/client'

export function Learn({
  category,
  sessionId,
  onBack,
  onChoose,
}: {
  category: string
  sessionId: string
  onBack: () => void
  onChoose: (levelId: string) => void
}) {
  const [vuln, setVuln] = useState<VulnerabilityEntry | null>(null)

  useEffect(() => {
    getVulnerabilities(sessionId).then((vulns) => {
      setVuln(vulns.find((v) => v.owasp_category === category) ?? null)
    })
  }, [category, sessionId])

  if (!vuln) {
    return <p className="p-10 text-[var(--text-muted)] font-mono">Loading…</p>
  }

  return (
    <main className="min-h-screen px-6 py-10 max-w-2xl mx-auto">
      <button
        onClick={onBack}
        className="mb-6 font-mono text-sm tracking-wide rounded border px-3 py-1.5 transition-shadow duration-200"
        style={{ borderColor: 'var(--surface-border)', color: 'var(--text-muted)' }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'var(--text)'
          e.currentTarget.style.color = 'var(--text)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'var(--surface-border)'
          e.currentTarget.style.color = 'var(--text-muted)'
        }}
      >
        ← back to vulnerabilities
      </button>

      <span
        className="font-mono text-xs px-2 py-0.5 rounded border inline-block mb-3"
        style={{ borderColor: 'var(--surface-border)', color: 'var(--text-muted)' }}
      >
        {vuln.owasp_category}
      </span>
      <p className="text-base leading-relaxed mb-8">{vuln.intro}</p>

      <div className="flex gap-6">
        <button
          onClick={() => onChoose(vuln.red_level_id)}
          className="flex-1 rounded-lg border-2 px-6 py-8 text-left transition-shadow duration-200 hover:shadow-[0_0_28px_var(--red-glow)]"
          style={{ borderColor: 'var(--red-accent)', background: 'var(--red-accent-dim)' }}
        >
          <span className="block font-mono text-lg tracking-wide" style={{ color: 'var(--red-accent)' }}>
            EXPLOIT IT
          </span>
          <span className="block mt-2 text-sm text-[var(--text-muted)]">
            Play the attacker.{vuln.exploited ? ' Already exploited this session.' : ''}
          </span>
        </button>

        <button
          onClick={() => onChoose(vuln.blue_level_id)}
          className="flex-1 rounded-lg border-2 px-6 py-8 text-left transition-shadow duration-200 hover:shadow-[0_0_28px_var(--blue-glow)]"
          style={{ borderColor: 'var(--blue-accent)', background: 'var(--blue-accent-dim)' }}
        >
          <span className="block font-mono text-lg tracking-wide" style={{ color: 'var(--blue-accent)' }}>
            PATCH IT
          </span>
          <span className="block mt-2 text-sm text-[var(--text-muted)]">
            Play the defender.{vuln.patched ? ' Already patched this session.' : ''}
          </span>
        </button>
      </div>
    </main>
  )
}
