"""Session and message models."""
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OnshapeTarget(BaseModel):
    document_id: str = ""
    workspace_id: str = ""
    element_id: str = ""


class SessionCreate(BaseModel):
    material: str = "PLA"
    onshape: OnshapeTarget | None = None
    pipeline_mode: str | None = None


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    material: str = "PLA"
    pipeline_mode: str = "auto"
    claude_session_id: str = Field(default_factory=lambda: str(uuid4()))
    has_prior_turn: bool = False
    onshape: OnshapeTarget = Field(default_factory=OnshapeTarget)
    status: str = "active"
    last_job_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageCreate(BaseModel):
    content: str
    attachments: list[str] = Field(default_factory=list)


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: str
    content: str
    created_at: datetime = Field(default_factory=utcnow)
    job_id: str | None = None


class SessionResponse(BaseModel):
    session: Session
    messages: list[Message] = Field(default_factory=list)
