"""Pipeline orchestrator: prompt → 3D model via Onshape MCP or CadQuery fallback."""
from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings
from ..models.events import PipelineEvent
from ..models.job import Job
from ..models.session import Message, Session
from . import cadquery_runner, claude_cli, skill_loader
from .session_store import store

log = logging.getLogger(__name__)


def session_data_dir(session_id: str) -> Path:
    return settings.data_dir / session_id


def exports_dir(session_id: str) -> Path:
    d = session_data_dir(session_id) / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def renders_dir(session_id: str) -> Path:
    d = session_data_dir(session_id) / "renders"
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_pipeline_mode(session: Session) -> str:
    mode = (session.pipeline_mode or settings.pipeline_mode).lower()
    log.info("Resolving pipeline mode: %s", mode)
    try:
        if mode != "auto":
            return mode
        if session.onshape.document_id and session.onshape.workspace_id:
            if claude_cli.claude_available():
                mode = "onshape"
                return mode
        if cadquery_runner.cadquery_available():
            mode = "cadquery"
            return mode
        mode = "demo"
        return mode
    finally:
        log.info("Resolved pipeline mode: %s", mode)


async def emit(job_id: str, event: PipelineEvent) -> None:
    payload = event.model_dump(exclude_none=True)
    await store.append_event(job_id, payload)


async def run_job(job_id: str) -> None:
    job = await store.get_job(job_id)
    if not job:
        return
    session = await store.get_session(job.session_id)
    if not session:
        job.status = "failed"
        job.error = "Session not found"
        await store.save_job(job)
        return

    job.status = "reasoning"
    job.started_at = datetime.now(timezone.utc)
    await store.save_job(job)

    mode = resolve_pipeline_mode(session)
    job.pipeline_mode = mode
    await store.save_job(job)

    try:
        if mode == "onshape":
            log.info("Running onshape pipeline")
            await _run_onshape_pipeline(job, session)
        elif mode == "cadquery":
            log.info("Running cadquery pipeline")
            await _run_cadquery_pipeline(job, session)
        else:
            log.info("Running demo pipeline")
            await _run_demo_pipeline(job, session)

        if await store.is_cancelled(job_id):
            job.status = "cancelled"
        elif job.status not in ("failed", "cancelled"):
            job.status = "completed"
    except Exception as exc:
        log.exception("Pipeline failed for job %s", job_id)
        job.status = "failed"
        job.error = str(exc)
        await emit(job_id, PipelineEvent(type="error", job_id=job_id, message=str(exc), recoverable=False))

    job.ended_at = datetime.now(timezone.utc)
    await store.save_job(job)

    session.updated_at = datetime.now(timezone.utc)
    session.has_prior_turn = True
    session.last_job_id = job_id
    await store.save_session(session)


async def _run_onshape_pipeline(job: Job, session: Session) -> None:
    await emit(job.id, PipelineEvent(type="phase", job_id=job.id, phase="spatial", text="Running spatial reasoning…"))
    await emit(job.id, PipelineEvent(type="phase", job_id=job.id, phase="material", text=f"Material: {session.material}"))

    system_prompt = skill_loader.load_onshape_system_prompt()
    onshape = session.onshape
    target = ""
    if onshape.document_id:
        target = (
            f"Target document_id={onshape.document_id}, "
            f"workspace_id={onshape.workspace_id}, "
            f"element_id={onshape.element_id}.\n\n"
        )

    full_prompt = (
        f"{target}"
        f"Material constraint: {session.material}.\n\n"
        f"User request: {job.prompt}"
    )

    job.status = "mcp_running"
    await store.save_job(job)

    async for event in claude_cli.run_claude_stream(
        prompt=full_prompt,
        system_prompt=system_prompt,
        session_id=session.claude_session_id,
        is_resume=session.has_prior_turn,
        job_id=job.id,
    ):
        if await store.is_cancelled(job.id):
            break
        await emit(job.id, event)
        job.events_count += 1

    await _try_collect_exports(job, session)


async def _run_cadquery_pipeline(job: Job, session: Session) -> None:
    await emit(job.id, PipelineEvent(type="phase", job_id=job.id, phase="spatial", text="Planning geometry…"))
    await emit(job.id, PipelineEvent(type="phase", job_id=job.id, phase="cadquery", text="Generating CadQuery code…"))

    system_prompt = skill_loader.load_cadquery_system_prompt()
    code_prompt = (
        f"Generate a complete CadQuery script for: {job.prompt}\n"
        f"Material: {session.material}. Export to output.step and output.stl."
    )

    job.status = "cadquery"
    await store.save_job(job)

    if claude_cli.claude_available():
        result = await claude_cli.run_claude_simple(
            prompt=code_prompt,
            system_prompt=system_prompt,
            session_id=session.claude_session_id,
            is_resume=session.has_prior_turn,
            allowed_tools="",
        )
        code = claude_cli.extract_python_code(result.get("stdout", ""))
        if result.get("stdout"):
            await emit(
                job.id,
                PipelineEvent(type="assistant_delta", job_id=job.id, text=result["stdout"][:4000]),
            )
    else:
        code = None

    if not code:
        code = cadquery_runner.build_demo_script(job.prompt, session.material)
        await emit(
            job.id,
            PipelineEvent(type="assistant_delta", job_id=job.id, text="Using parametric demo box template."),
        )

    work_dir = session_data_dir(session.id) / "work" / job.id
    exec_result = await cadquery_runner.execute_cadquery_script(
        code, work_dir, timeout=settings.cadquery_timeout_s
    )

    if not exec_result["ok"]:
        job.status = "failed"
        job.error = exec_result.get("stderr") or exec_result.get("error") or "CadQuery failed"
        await emit(job.id, PipelineEvent(type="error", job_id=job.id, message=job.error, recoverable=True))
        return

    await _copy_exports(job, session, exec_result.get("stl_path"), exec_result.get("step_path"))


async def _run_demo_pipeline(job: Job, session: Session) -> None:
    """Demo mode: no Claude/MCP — generate a simple parametric box."""
    await emit(job.id, PipelineEvent(type="phase", job_id=job.id, phase="spatial", text="Demo mode: parsing dimensions…"))
    await emit(
        job.id,
        PipelineEvent(
            type="reasoning",
            job_id=job.id,
            text="Functional decomposition: rectangular shell box from parsed dimensions.",
        ),
    )
    await emit(job.id, PipelineEvent(type="phase", job_id=job.id, phase="cadquery", text="Building demo model…"))

    code = cadquery_runner.build_demo_script(job.prompt, session.material)
    work_dir = session_data_dir(session.id) / "work" / job.id

    if cadquery_runner.cadquery_available():
        exec_result = await cadquery_runner.execute_cadquery_script(code, work_dir)
        if exec_result["ok"]:
            await _copy_exports(job, session, exec_result.get("stl_path"), exec_result.get("step_path"))
            await emit(
                job.id,
                PipelineEvent(
                    type="assistant_delta",
                    job_id=job.id,
                    text="Demo model generated. Configure Claude CLI + MCP for full AI pipeline.",
                ),
            )
            return

    # Pure-Python STL fallback without CadQuery
    await _write_minimal_stl(job, session, job.prompt)
    await emit(
        job.id,
        PipelineEvent(
            type="assistant_delta",
            job_id=job.id,
            text="Generated minimal STL (CadQuery not installed). Install CadQuery for richer geometry.",
        ),
    )


async def _copy_exports(
    job: Job,
    session: Session,
    stl_path: str | None,
    step_path: str | None,
) -> None:
    out = exports_dir(session.id)
    if stl_path and Path(stl_path).exists():
        dest = out / "part.stl"
        shutil.copy2(stl_path, dest)
        url = f"/api/files/{session.id}/part.stl"
        job.result["stl_url"] = url
        await emit(
            job.id,
            PipelineEvent(type="file", job_id=job.id, url=url, format="stl"),
        )
    if step_path and Path(step_path).exists():
        dest = out / "part.step"
        shutil.copy2(step_path, dest)
        url = f"/api/files/{session.id}/part.step"
        job.result["step_url"] = url
        await emit(
            job.id,
            PipelineEvent(type="file", job_id=job.id, url=url, format="step"),
        )
    await store.save_job(job)
    await emit(job.id, PipelineEvent(type="phase", job_id=job.id, phase="export", text="Exports ready"))


async def _write_minimal_stl(job: Job, session: Session, prompt: str) -> None:
    """Write a trivial ASCII STL box when CadQuery is unavailable."""
    length, width, height, _ = cadquery_runner.parse_box_dimensions(prompt)
    out = exports_dir(session.id) / "part.stl"

    def v(x: float, y: float, z: float) -> str:
        return f"      vertex {x:.4f} {y:.4f} {z:.4f}\n"

    lx, ly, lz = length / 2, width / 2, height / 2
    faces = [
        ((0, 0, 1), [(-lx, -ly, lz), (lx, -ly, lz), (lx, ly, lz)]),
        ((0, 0, 1), [(-lx, -ly, lz), (lx, ly, lz), (-lx, ly, lz)]),
        ((0, 0, -1), [(-lx, ly, -lz), (lx, ly, -lz), (lx, -ly, -lz)]),
        ((0, 0, -1), [(-lx, ly, -lz), (lx, -ly, -lz), (-lx, -ly, -lz)]),
        ((0, 1, 0), [(-lx, ly, -lz), (-lx, ly, lz), (lx, ly, lz)]),
        ((0, 1, 0), [(-lx, ly, -lz), (lx, ly, lz), (lx, ly, -lz)]),
        ((0, -1, 0), [(-lx, -ly, lz), (-lx, -ly, -lz), (lx, -ly, -lz)]),
        ((0, -1, 0), [(-lx, -ly, lz), (lx, -ly, -lz), (lx, -ly, lz)]),
        ((1, 0, 0), [(lx, -ly, -lz), (lx, ly, -lz), (lx, ly, lz)]),
        ((1, 0, 0), [(lx, -ly, -lz), (lx, ly, lz), (lx, -ly, lz)]),
        ((-1, 0, 0), [(-lx, -ly, lz), (-lx, ly, lz), (-lx, ly, -lz)]),
        ((-1, 0, 0), [(-lx, -ly, lz), (-lx, ly, -lz), (-lx, -ly, -lz)]),
    ]

    lines = ["solid demo_box\n"]
    for normal, verts in faces:
        lines.append(f"  facet normal {normal[0]} {normal[1]} {normal[2]}\n")
        lines.append("    outer loop\n")
        for pt in verts:
            lines.append(v(*pt))
        lines.append("    endloop\n")
        lines.append("  endfacet\n")
    lines.append("endsolid demo_box\n")
    out.write_text("".join(lines))

    url = f"/api/files/{session.id}/part.stl"
    job.result["stl_url"] = url
    await emit(job.id, PipelineEvent(type="file", job_id=job.id, url=url, format="stl"))
    await store.save_job(job)


async def _try_collect_exports(job: Job, session: Session) -> None:
    """After Onshape MCP run, check for any pre-exported files in session dir."""
    out = exports_dir(session.id)
    for name, fmt in [("part.stl", "stl"), ("part.step", "step")]:
        path = out / name
        if path.exists():
            url = f"/api/files/{session.id}/{name}"
            job.result[f"{fmt}_url"] = url
            await emit(job.id, PipelineEvent(type="file", job_id=job.id, url=url, format=fmt))
    await store.save_job(job)


def enqueue_job(session: Session, prompt: str) -> Job:
    job = Job(session_id=session.id, prompt=prompt, pipeline_mode=resolve_pipeline_mode(session))
    return job


async def start_job(session: Session, user_message: Message) -> Job:
    job = enqueue_job(session, user_message.content)
    await store.save_job(job)
    user_message.job_id = job.id
    await store.add_message(session.id, user_message)

    assistant_msg = Message(role="assistant", content="", job_id=job.id)
    await store.add_message(session.id, assistant_msg)

    asyncio.create_task(run_job(job.id))
    return job
