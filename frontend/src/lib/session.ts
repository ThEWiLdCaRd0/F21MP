const SESSION_KEY = 'redblue_session_id'

export function getSessionId(): string {
  let id = localStorage.getItem(SESSION_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(SESSION_KEY, id)
  }
  return id
}

export function resetSessionId(): void {
  localStorage.removeItem(SESSION_KEY)
}
