export type Role = 'red' | 'blue'

export type ProgressEntry = {
  level_id: string
  completed_at: string | null
  attempts: number
}

export async function getProgress(sessionId: string): Promise<ProgressEntry[]> {
  const res = await fetch(`/api/progress?session_id=${sessionId}`)
  return res.json()
}

export type VulnerabilityEntry = {
  owasp_category: string
  order: number
  intro: string
  red_level_id: string
  blue_level_id: string
  exploited: boolean
  patched: boolean
}

export async function getVulnerabilities(sessionId: string): Promise<VulnerabilityEntry[]> {
  const res = await fetch(`/api/vulnerabilities?session_id=${sessionId}`)
  return res.json()
}

export type VictimPcState = {
  files: string[]
  services: string[]
  logs: string[]
}

export type LevelDetail = {
  id: string
  role: Role
  order: number
  owasp_category: string
  title: string
  difficulty: number
  objective: string
  briefing: string
  hints: string[]
  victim_pc_initial_state: VictimPcState
  randomizable_fields: string[]
}

export type CommandResult = {
  terminal_output: string
  victim_pc_state: VictimPcState
  wins_level: boolean
  debrief: string | null
}

export async function getLevelDetail(levelId: string, sessionId: string): Promise<LevelDetail> {
  const res = await fetch(`/api/levels/${levelId}/detail?session_id=${sessionId}`)
  return res.json()
}

export async function postCommand(levelId: string, sessionId: string, input: string): Promise<CommandResult> {
  const res = await fetch(`/api/levels/${levelId}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, input }),
  })
  return res.json()
}
