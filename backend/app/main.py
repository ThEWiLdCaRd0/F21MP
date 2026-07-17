from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_connection, init_db
from app.models import (
    CommandRequest,
    CommandResult,
    LevelDetail,
    LevelStub,
    ProgressEntry,
    VulnerabilityEntry,
)
from app.services import command_engine

app = FastAPI(title="Red/Blue API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    command_engine.get_levels()  # fail fast on malformed level content, not on first request
    command_engine.get_intros()  # same - fail fast on malformed vulnerability_intros.json


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/levels")
def list_levels(role: Literal["red", "blue"] | None = None) -> list[LevelStub]:
    levels = [LevelStub(**level) for level in command_engine.get_levels().values()]
    levels.sort(key=lambda level: (level.role, level.order))
    if role is None:
        return levels
    return [level for level in levels if level.role == role]


@app.get("/api/vulnerabilities")
def list_vulnerabilities(session_id: str = Query(..., min_length=1, max_length=128)) -> list[VulnerabilityEntry]:
    return [VulnerabilityEntry(**v) for v in command_engine.get_vulnerabilities(session_id)]


@app.get("/api/progress")
def get_progress(session_id: str = Query(..., min_length=1, max_length=128)) -> list[ProgressEntry]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT level_id, completed_at, attempts FROM progress WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    return [ProgressEntry(**dict(row)) for row in rows]


@app.get("/api/levels/{level_id}/detail")
def get_level_detail(level_id: str, session_id: str = Query(..., min_length=1, max_length=128)) -> LevelDetail:
    # Fetched per-session (not the raw template) so a session's briefing/hints always
    # agree with whatever randomized values its commands were materialized against.
    level = command_engine.get_level_for_session(session_id, level_id)
    if level is None:
        raise HTTPException(status_code=404, detail="level not found")
    # commands + debrief intentionally excluded — the answer key and its explanation,
    # never sent before the level is actually won (see command_engine.run_command).
    return LevelDetail(**{key: value for key, value in level.items() if key not in ("commands", "debrief")})


@app.post("/api/levels/{level_id}/command")
def post_command(level_id: str, body: CommandRequest) -> CommandResult:
    try:
        result = command_engine.run_command(level_id, body.session_id, body.input)
    except KeyError:
        raise HTTPException(status_code=404, detail="level not found")
    return CommandResult(**result)
