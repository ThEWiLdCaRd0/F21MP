import { useState } from 'react'
import { Landing } from './pages/Landing'
import { VulnerabilityHub } from './pages/VulnerabilityHub'
import { Learn } from './pages/Learn'
import { LevelView } from './pages/LevelView'
import { getSessionId } from './lib/session'

function App() {
  const [started, setStarted] = useState(false)
  const [category, setCategory] = useState<string | null>(null)
  const [levelId, setLevelId] = useState<string | null>(null)

  if (!started) {
    return <Landing onStart={() => setStarted(true)} />
  }

  const sessionId = getSessionId()

  if (levelId) {
    return <LevelView levelId={levelId} sessionId={sessionId} onBack={() => setLevelId(null)} />
  }

  if (category) {
    return (
      <Learn category={category} sessionId={sessionId} onBack={() => setCategory(null)} onChoose={setLevelId} />
    )
  }

  return <VulnerabilityHub sessionId={sessionId} onBack={() => setStarted(false)} onSelect={setCategory} />
}

export default App
