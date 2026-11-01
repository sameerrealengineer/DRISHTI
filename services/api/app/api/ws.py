"""WebSocket endpoint /api/v1/ws (PRD §15.9). Token auth and role/area filtering arrive in M3."""

import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.risk.service import risk_service
from app.sim.state import sim_clock
from app.ws.hub import hub, make_event

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str | None = None):
    await hub.connect(ws)
    try:
        # Initial snapshot so a new client renders immediately.
        await ws.send_json(make_event("sim.tick", sim_clock.state()))
        if risk_service.scenario is not None:
            latest = risk_service.latest(sim_clock.t)
            await ws.send_json(
                make_event(
                    "risk.updated",
                    {"t": latest["t"], "areas": latest["areas"], "early_warning": latest["early_warning"]},
                )
            )
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        with contextlib.suppress(Exception):
            hub.disconnect(ws)
