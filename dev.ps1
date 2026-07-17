# Launches the whole project: backend (FastAPI) + frontend (Vite) each in their own
# window, so you can watch logs / Ctrl+C them independently. Run from anywhere:
#   .\dev.ps1

$root = $PSScriptRoot

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .venv\Scripts\python.exe run.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Write-Host "Backend:  http://localhost:8000"
Write-Host "Frontend: http://localhost:5173"

try {
    # 127.0.0.1, not localhost - Ollama binds IPv4 only, and localhost resolves to
    # ::1 first on this machine, which times out instead of falling back to IPv4.
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
} catch {
    Write-Host "Note: Ollama doesn't seem to be running - the randomizer will fall back to default values." -ForegroundColor Yellow
}
