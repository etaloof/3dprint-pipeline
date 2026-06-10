"""SSE / pipeline event types."""
from typing import Any, Literal

from pydantic import BaseModel, Field


Phase = Literal["spatial", "material", "mcp", "cadquery", "verify", "export", "done"]


class PipelineEvent(BaseModel):
    type: str
    job_id: str | None = None
    phase: Phase | None = None
    text: str | None = None
    name: str | None = None
    args: dict[str, Any] | None = None
    ok: bool | None = None
    summary: str | None = None
    url: str | None = None
    view: Literal["iso", "front", "top"] | None = None
    format: Literal["stl", "step", "png"] | None = None
    message: str | None = None
    recoverable: bool | None = None
    feature_count: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_sse(self) -> str:
        return self.model_dump_json(exclude_none=True)
