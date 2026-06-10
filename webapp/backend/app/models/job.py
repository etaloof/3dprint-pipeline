"""Job tracking models."""
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


JobStatus = str  # queued | reasoning | mcp_running | cadquery | verifying | exporting | completed | failed | cancelled


class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    status: JobStatus = "queued"
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    prompt: str = ""
    error: str | None = None
    events_count: int = 0
    pipeline_mode: str = "auto"
    result: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job: Job
    events: list[dict[str, Any]] = Field(default_factory=list)
