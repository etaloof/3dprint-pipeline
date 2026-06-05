"""Session and job persistence (Redis with in-memory fallback)."""
from __future__ import annotations

import json
import logging
from typing import Any

from ..config import settings
from ..models.job import Job
from ..models.session import Message, Session

log = logging.getLogger(__name__)


class SessionStore:
    def __init__(self) -> None:
        self._memory_sessions: dict[str, Session] = {}
        self._memory_messages: dict[str, list[Message]] = {}
        self._memory_jobs: dict[str, Job] = {}
        self._memory_events: dict[str, list[dict[str, Any]]] = {}
        self._redis = None

    async def connect(self) -> None:
        if not settings.use_redis:
            return
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
            await self._redis.ping()
            log.info("Connected to Redis at %s", settings.redis_url)
        except Exception as exc:
            log.warning("Redis unavailable (%s); using in-memory store", exc)
            self._redis = None

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    def _session_key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _messages_key(self, session_id: str) -> str:
        return f"session:{session_id}:messages"

    def _job_key(self, job_id: str) -> str:
        return f"job:{job_id}"

    def _events_key(self, job_id: str) -> str:
        return f"job:{job_id}:events"

    async def save_session(self, session: Session) -> None:
        payload = session.model_dump_json()
        if self._redis:
            await self._redis.set(self._session_key(session.id), payload)
        else:
            self._memory_sessions[session.id] = session

    async def get_session(self, session_id: str) -> Session | None:
        if self._redis:
            raw = await self._redis.get(self._session_key(session_id))
            if not raw:
                return None
            return Session.model_validate_json(raw)
        return self._memory_sessions.get(session_id)

    async def add_message(self, session_id: str, message: Message) -> None:
        if self._redis:
            await self._redis.rpush(self._messages_key(session_id), message.model_dump_json())
        else:
            self._memory_messages.setdefault(session_id, []).append(message)

    async def list_messages(self, session_id: str) -> list[Message]:
        if self._redis:
            raw_list = await self._redis.lrange(self._messages_key(session_id), 0, -1)
            return [Message.model_validate_json(x) for x in raw_list]
        return list(self._memory_messages.get(session_id, []))

    async def save_job(self, job: Job) -> None:
        if self._redis:
            await self._redis.set(self._job_key(job.id), job.model_dump_json())
        else:
            self._memory_jobs[job.id] = job

    async def get_job(self, job_id: str) -> Job | None:
        if self._redis:
            raw = await self._redis.get(self._job_key(job_id))
            if not raw:
                return None
            return Job.model_validate_json(raw)
        return self._memory_jobs.get(job_id)

    async def append_event(self, job_id: str, event: dict[str, Any]) -> None:
        if self._redis:
            await self._redis.rpush(self._events_key(job_id), json.dumps(event))
        else:
            self._memory_events.setdefault(job_id, []).append(event)

    async def list_events(self, job_id: str, after: int = 0) -> list[dict[str, Any]]:
        if self._redis:
            raw_list = await self._redis.lrange(self._events_key(job_id), after, -1)
            return [json.loads(x) for x in raw_list]
        return self._memory_events.get(job_id, [])[after:]

    async def set_cancel_flag(self, job_id: str) -> None:
        if self._redis:
            await self._redis.set(f"job:{job_id}:cancel", "1", ex=3600)
        else:
            job = self._memory_jobs.get(job_id)
            if job:
                job.status = "cancelled"

    async def is_cancelled(self, job_id: str) -> bool:
        if self._redis:
            return bool(await self._redis.get(f"job:{job_id}:cancel"))
        job = self._memory_jobs.get(job_id)
        return job is not None and job.status == "cancelled"


store = SessionStore()
