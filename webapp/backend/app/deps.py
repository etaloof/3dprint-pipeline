"""FastAPI dependencies."""
from fastapi import Header, HTTPException

from .config import settings


async def optional_api_auth(authorization: str | None = Header(default=None)) -> None:
    if not settings.api_secret:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.api_secret:
        raise HTTPException(status_code=403, detail="Invalid API token")
