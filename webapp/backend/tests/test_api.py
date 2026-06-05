"""API smoke tests (no Claude/MCP required)."""
import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("USE_REDIS", "false")
os.environ.setdefault("DATA_DIR", "/tmp/3dpp-pytest")
os.environ.setdefault("SKILLS_DIR", str(Path(__file__).resolve().parents[3] / "skills"))
os.environ.setdefault("PIPELINE_MODE", "demo")

from app.main import app  # noqa: E402


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_materials():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/materials")
    assert res.status_code == 200
    assert len(res.json()["materials"]) > 0


@pytest.mark.asyncio
async def test_demo_pipeline_produces_stl():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        session_res = await client.post("/api/sessions", json={"material": "PLA", "pipeline_mode": "demo"})
        assert session_res.status_code == 200
        session_id = session_res.json()["session"]["id"]

        msg_res = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"content": "50x40x30mm box"},
        )
        assert msg_res.status_code == 200
        job_id = msg_res.json()["job_id"]

        import asyncio

        for _ in range(40):
            job_res = await client.get(f"/api/jobs/{job_id}")
            job = job_res.json()["job"]
            if job["status"] in ("completed", "failed", "cancelled"):
                break
            await asyncio.sleep(0.25)

        assert job["status"] == "completed"
        files_res = await client.get(f"/api/sessions/{session_id}/files")
        names = [f["name"] for f in files_res.json()["files"]]
        assert "part.stl" in names
