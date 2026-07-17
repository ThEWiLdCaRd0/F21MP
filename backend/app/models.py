from typing import Literal

from pydantic import BaseModel, Field


class LevelStub(BaseModel):
    id: str
    role: Literal["red", "blue"]
    order: int
    owasp_category: str
    title: str
    difficulty: int


class VulnerabilityEntry(BaseModel):
    owasp_category: str
    order: int
    intro: str
    red_level_id: str
    blue_level_id: str
    exploited: bool
    patched: bool


class ProgressEntry(BaseModel):
    level_id: str
    completed_at: str | None
    attempts: int


class LevelDetail(BaseModel):
    id: str
    role: Literal["red", "blue"]
    order: int
    owasp_category: str
    title: str
    difficulty: int
    objective: str
    briefing: str
    hints: list[str]
    victim_pc_initial_state: dict
    randomizable_fields: list[str]


class CommandRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    input: str = Field(min_length=1, max_length=2000)


class CommandResult(BaseModel):
    terminal_output: str
    victim_pc_state: dict
    wins_level: bool
    debrief: str | None = None
