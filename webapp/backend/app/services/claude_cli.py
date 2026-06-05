"""Claude Code CLI integration for Onshape MCP pipeline."""
from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

from ..config import settings
from ..models.events import PipelineEvent
from .mcp_client import build_mcp_config

log = logging.getLogger(__name__)

TOOL_CALL_RE = re.compile(
    r"(?:mcp__onshape__|onshape__)([a-z_]+)",
    re.IGNORECASE,
)


def claude_available() -> bool:
    return bool(shutil.which(settings.claude_cli))


def resolve_claude_mode() -> str:
    mode = settings.claude_mode.lower()
    if mode in ("cli", "api", "demo"):
        return mode
    if claude_available() and settings.anthropic_api_key:
        return "cli"
    if claude_available():
        return "cli"
    if settings.anthropic_api_key:
        return "api"
    return "demo"


async def run_claude_stream(
    *,
    prompt: str,
    system_prompt: str,
    session_id: str,
    is_resume: bool,
    job_id: str,
    allowed_tools: str = "mcp__onshape__*",
    mcp_config_dir: Path | None = None,
) -> AsyncIterator[PipelineEvent]:
    """Run Claude CLI and yield parsed pipeline events."""
    if not claude_available():
        yield PipelineEvent(
            type="error",
            job_id=job_id,
            message="Claude CLI not found. Set CLAUDE_MODE=demo or install claude.",
            recoverable=False,
        )
        return

    tmp = mcp_config_dir or Path("/tmp/3dpp_mcp")
    mcp_config = build_mcp_config(tmp)

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    cmd = [
        settings.claude_cli,
        "--print",
        "--model",
        settings.claude_model,
        "--system-prompt",
        system_prompt,
        "--mcp-config",
        str(mcp_config),
        "--allowedTools",
        allowed_tools,
    ]
    if is_resume:
        cmd += ["--resume", session_id]
    else:
        cmd += ["--session-id", session_id]
    cmd.append(prompt)

    yield PipelineEvent(type="phase", job_id=job_id, phase="mcp", text="Starting Claude agent…")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )

    assert proc.stdout is not None
    buffer = ""
    async for chunk in proc.stdout:
        text = chunk.decode(errors="replace")
        buffer += text
        yield PipelineEvent(type="assistant_delta", job_id=job_id, text=text)

        for match in TOOL_CALL_RE.finditer(text):
            yield PipelineEvent(
                type="tool_call",
                job_id=job_id,
                name=f"onshape__{match.group(1)}",
                summary=match.group(0),
            )

    rc = await proc.wait()
    if rc != 0:
        yield PipelineEvent(
            type="error",
            job_id=job_id,
            message=f"Claude CLI exited with code {rc}",
            recoverable=False,
            extra={"tail": buffer[-2000:]},
        )
    else:
        yield PipelineEvent(type="phase", job_id=job_id, phase="verify", text="Agent completed")


async def run_claude_simple(
    *,
    prompt: str,
    system_prompt: str,
    session_id: str,
    is_resume: bool,
    allowed_tools: str = "",
    timeout: int | None = None,
) -> dict:
    """Blocking-style Claude call returning stdout text."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    cmd = [
        settings.claude_cli,
        "--print",
        "--model",
        settings.claude_model,
        "--system-prompt",
        system_prompt,
    ]
    if allowed_tools:
        tmp = Path("/tmp/3dpp_mcp")
        mcp_config = build_mcp_config(tmp)
        cmd += ["--mcp-config", str(mcp_config), "--allowedTools", allowed_tools]
    else:
        cmd += ["--tools", ""]
    if is_resume:
        cmd += ["--resume", session_id]
    else:
        cmd += ["--session-id", session_id]
    cmd.append(prompt)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout or settings.claude_timeout_s,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "returncode": proc.returncode,
        }
    except asyncio.TimeoutError:
        return {"ok": False, "stdout": "", "stderr": "timeout", "returncode": -1}


def extract_python_code(response_text: str) -> str | None:
    match = re.search(r"```python\s*\n(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*\n(.*?)```", response_text, re.DOTALL)
    if match:
        code = match.group(1).strip()
        if "import cadquery" in code or "cadquery as cq" in code:
            return code
    return None
