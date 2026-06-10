"""MCP configuration and connectivity helpers."""
import json
import shutil
import subprocess
from pathlib import Path

from ..config import settings


def build_mcp_config(tmp_dir: Path, sse_url: str | None = None) -> Path:
    """Write mcp.json pointing at the Jarvis Onshape SSE endpoint."""
    url = sse_url or settings.mcp_sse_url
    cfg = {
        "mcpServers": {
            "onshape": {
                "command": "uvx",
                "args": ["mcp-proxy", url],
            },
            "cadquery": {
                "command": "node",
                "args": [str(settings.project_root / "mcp-cadquery-server" / "dist" / "index.js")],
            },
        }
    }
    tmp_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = tmp_dir / "mcp.json"
    cfg_path.write_text(json.dumps(cfg, indent=2))
    return cfg_path


def check_mcp_reachable(timeout: int = 5) -> bool:
    """Best-effort check that mcp-proxy and uvx are available."""
    if not shutil.which("uvx"):
        return False
    try:
        proc = subprocess.run(
            ["uvx", "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_claude_cli(timeout: int = 5) -> bool:
    cli = settings.claude_cli
    if not shutil.which(cli):
        return False
    try:
        proc = subprocess.run(
            [cli, "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
