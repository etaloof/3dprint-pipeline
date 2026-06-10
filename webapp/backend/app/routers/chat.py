"""Chat streaming via SSE."""
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from ..deps import optional_api_auth
from ..models.session import Message, Session
from ..services.pipeline import start_job
from ..services.session_store import store

router = APIRouter(dependencies=[Depends(optional_api_auth)])


async def start_message_job(session: Session, user_message: Message):
    return await start_job(session, user_message)


@router.get("/api/sessions/{session_id}/stream")
async def stream_session(
    session_id: str,
    job_id: str = Query(...),
):
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    job = await store.get_job(job_id)
    if not job or job.session_id != session_id:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        sent = 0
        while True:
            events = await store.list_events(job_id, after=sent)
            for ev in events:
                sent += 1
                yield {"event": "message", "data": json.dumps(ev)}

            current = await store.get_job(job_id)
            if current and current.status in ("completed", "failed", "cancelled"):
                if sent >= len(await store.list_events(job_id)):
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "done", "job_id": job_id, "status": current.status}),
                    }
                    break
            await asyncio.sleep(0.3)

    return EventSourceResponse(event_generator())
