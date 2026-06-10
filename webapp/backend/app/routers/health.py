"""Health check endpoint."""
import shutil

from fastapi import APIRouter

from ..config import settings
from ..services import cadquery_runner, claude_cli, mcp_client

router = APIRouter()


@router.get("/api/health")
async def health():
    claude_mode = claude_cli.resolve_claude_mode()
    return {
        "status": "ok",
        "claude_mode": claude_mode,
        "claude_cli": mcp_client.check_claude_cli(),
        "mcp_proxy": mcp_client.check_mcp_reachable(),
        "cadquery": cadquery_runner.cadquery_available(),
        "pipeline_mode": settings.pipeline_mode,
        "skills_dir": str(settings.resolved_skills_dir()),
        "data_dir": str(settings.data_dir),
    }
