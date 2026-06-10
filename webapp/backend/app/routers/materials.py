"""Materials endpoint."""
import json

from fastapi import APIRouter, HTTPException

from ..config import settings

router = APIRouter()

_cache: dict | None = None


def _load_materials() -> dict:
    global _cache
    if _cache is None:
        path = settings.resolved_materials_file()
        if not path.exists():
            raise HTTPException(status_code=500, detail=f"materials.json not found at {path}")
        with open(path) as f:
            _cache = json.load(f)
    return _cache


@router.get("/api/materials")
async def get_materials():
    data = _load_materials()
    materials = []
    for key, info in data.items():
        materials.append(
            {
                "id": key,
                "name": info.get("full_name", key),
                "wall_min_mm": info.get("wall_min_mm"),
                "temp_max_service": info.get("temp_max_service"),
            }
        )
    return {"materials": materials}


@router.get("/api/materials/{material_id}")
async def get_material(material_id: str):
    data = _load_materials()
    if material_id not in data:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"id": material_id, **data[material_id]}
