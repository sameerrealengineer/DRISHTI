"""WebSocket fan-out (PRD §15.9). Events are `{type, data, at}`.

Each API process keeps its own sockets. Events are also published on Redis so
other processes (more API replicas, Celery workers) reach every client. If Redis
is down, events still reach this process's clients.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)
CHANNEL = "drishti:events"


def make_event(type_: str, data: Any) -> dict[str, Any]:
    return {"type": type_, "data": data, "at": datetime.now(UTC).isoformat()}


class Hub:
    def __init__(self) -> None:
        self.sockets: set[WebSocket] = set()
        self.origin = uuid.uuid4().hex
        self._redis = None
        self._task: asyncio.Task | None = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.sockets.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.sockets.discard(ws)

    async def _local(self, event: dict[str, Any]) -> None:
        dead = []
        msg = json.dumps(event, default=str)
        for ws in list(self.sockets):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def publish(self, type_: str, data: Any) -> dict[str, Any]:
        event = make_event(type_, data)
        await self._local(event)
        if self._redis is not None:
            try:
                await self._redis.publish(
                    CHANNEL, json.dumps({"origin": self.origin, "event": event}, default=str)
                )
            except Exception as exc:  # pragma: no cover - redis outage
                log.warning("redis publish failed: %s", exc)
        return event

    async def start(self, redis_url: str) -> None:
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(redis_url)
            await self._redis.ping()
        except Exception as exc:
            log.warning("redis unavailable, WS fan-out is local only: %s", exc)
            self._redis = None
            return
        self._task = asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        assert self._redis is not None
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            try:
                payload = json.loads(msg["data"])
            except (TypeError, ValueError):
                continue
            if payload.get("origin") != self.origin:
                await self._local(payload["event"])

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._redis is not None:
            await self._redis.aclose()


hub = Hub()


def publish_sync(redis_url: str, type_: str, data: Any) -> None:
    """For Celery workers / scripts: publish an event to all API processes."""
    import redis

    r = redis.from_url(redis_url)
    r.publish(CHANNEL, json.dumps({"origin": "worker", "event": make_event(type_, data)}, default=str))
