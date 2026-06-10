"""Session management endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import optional_api_auth
from ..models.session import Message, MessageCreate, OnshapeTarget, Session, SessionCreate, SessionResponse
from ..services.pipeline import resolve_pipeline_mode, start_job
from ..services.session_store import store

router = APIRouter(dependencies=[Depends(optional_api_auth)])


@router.post("/api/sessions", response_model=SessionResponse)
async def create_session(body: SessionCreate):
    onshape = body.onshape or OnshapeTarget()
    if not onshape.document_id and settings_onshape_defaults():
        onshape = settings_onshape_defaults()

    session = Session(
        material=body.material,
        pipeline_mode=body.pipeline_mode or "auto",
        onshape=onshape,
    )
    session.metadata["resolved_pipeline"] = resolve_pipeline_mode(session)
    await store.save_session(session)
    return SessionResponse(session=session, messages=[])


def settings_onshape_defaults() -> OnshapeTarget | None:
    from ..config import settings

    if settings.onshape_default_did and settings.onshape_default_wid:
        return OnshapeTarget(
            document_id=settings.onshape_default_did,
            workspace_id=settings.onshape_default_wid,
            element_id=settings.onshape_default_eid,
        )
    return None


@router.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await store.list_messages(session_id)
    return SessionResponse(session=session, messages=messages)


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "closed"
    await store.save_session(session)
    return {"ok": True}


@router.post("/api/sessions/{session_id}/messages")
async def post_message(session_id: str, body: MessageCreate):
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    user_msg = Message(role="user", content=body.content)
    job = await start_job(session, user_msg)
    return {"job_id": job.id, "session_id": session_id}
