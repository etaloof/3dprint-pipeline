"""File download and export listing."""
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..deps import optional_api_auth
from ..services.pipeline import exports_dir, renders_dir

router = APIRouter(dependencies=[Depends(optional_api_auth)])


def _safe_join(base: Path, filename: str) -> Path:
    name = Path(filename).name
    path = base / name
    if not path.resolve().is_relative_to(base.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path")
    return path


@router.get("/api/sessions/{session_id}/files")
async def list_files(session_id: str):
    exports = exports_dir(session_id)
    files = []
    if exports.exists():
        for p in sorted(exports.iterdir()):
            if p.is_file():
                files.append(
                    {
                        "name": p.name,
                        "format": p.suffix.lstrip(".").lower(),
                        "size": p.stat().st_size,
                        "url": f"/api/files/{session_id}/{p.name}",
                    }
                )
    return {"files": files}


@router.get("/api/sessions/{session_id}/renders")
async def list_renders(session_id: str):
    renders = renders_dir(session_id)
    items = []
    if renders.exists():
        for p in sorted(renders.iterdir()):
            if p.suffix.lower() in (".png", ".jpg", ".webp"):
                items.append({"view": p.stem, "url": f"/api/files/{session_id}/renders/{p.name}"})
    return {"renders": items}


@router.get("/api/files/{session_id}/{filename}")
async def get_export_file(session_id: str, filename: str):
    path = _safe_join(exports_dir(session_id), filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    mime, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=mime or "application/octet-stream", filename=path.name)


@router.get("/api/files/{session_id}/renders/{filename}")
async def get_render_file(session_id: str, filename: str):
    path = _safe_join(renders_dir(session_id), filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="image/png", filename=path.name)
