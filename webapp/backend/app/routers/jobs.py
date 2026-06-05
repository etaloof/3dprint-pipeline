"""Job status endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import optional_api_auth
from ..models.job import JobResponse
from ..services.session_store import store

router = APIRouter(dependencies=[Depends(optional_api_auth)])


@router.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    events = await store.list_events(job_id)
    return JobResponse(job=job, events=events)


@router.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await store.set_cancel_flag(job_id)
    job.status = "cancelled"
    await store.save_job(job)
    return {"ok": True, "job_id": job_id}
