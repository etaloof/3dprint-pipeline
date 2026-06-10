"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import chat, files, health, jobs, materials, sessions
from .services.session_store import store

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    await store.connect()
    yield
    await store.close()


app = FastAPI(
    title="3D Print Pipeline Web API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(materials.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(jobs.router)
app.include_router(files.router)
