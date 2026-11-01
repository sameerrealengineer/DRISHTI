"""Demo sim clock (PRD §12 DEMO-1/3). Replaces the wall clock in DEMO mode.

`t` is hours relative to landfall of the active scenario. At speed 1x, one sim
hour takes `sim_seconds_per_hour` real seconds. Every tick broadcasts
`sim.tick`; when the whole hour changes, `risk.updated` carries changed areas.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from sqlalchemy import select

from app import models as m
from app.config import get_settings
from app.db import session_factory
from app.risk.service import RiskService
from app.ws.hub import Hub

log = logging.getLogger(__name__)
SPEEDS = (1.0, 4.0, 16.0)
TICK_S = 1.0


class SimClock:
    def __init__(self, risk: RiskService, hub: Hub) -> None:
        self.risk = risk
        self.hub = hub
        self.scenario_key = get_settings().sim_default_scenario
        self.t = -24.0
        self.playing = False
        self.speed = 1.0
        self._hour: int | None = None
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    # -- state --------------------------------------------------------------

    def state(self) -> dict[str, Any]:
        scn = self.risk.scenario
        return {
            "scenario": self.scenario_key,
            "scenario_name": scn.name if scn else None,
            "t": round(self.t, 3),
            "hour": self.risk.hour_index(self.t) if scn else None,
            "sim_time": scn.sim_time(self.t).isoformat() if scn else None,
            "landfall_at": scn.landfall_at.isoformat() if scn else None,
            "t_min": scn.t_min if scn else None,
            "t_max": scn.t_max if scn else None,
            "playing": self.playing,
            "speed": self.speed,
            "speeds": list(SPEEDS),
            "demo_data": True,
        }

    def _persist(self) -> None:
        scn = self.risk.scenario
        if scn is None:
            return
        try:
            with session_factory()() as db:
                row = db.scalar(select(m.SimState).limit(1))
                if row is None:
                    row = m.SimState(scenario_key=self.scenario_key, sim_time=scn.sim_time(self.t))
                    db.add(row)
                row.scenario_key = self.scenario_key
                row.sim_time = scn.sim_time(self.t)
                row.playing = self.playing
                row.speed = self.speed
                db.commit()
        except Exception as exc:  # DB down should not stop the demo clock
            log.warning("sim_state persist failed: %s", exc)

    def restore(self) -> None:
        """Load persisted sim_state (if any) and the scenario."""
        try:
            with session_factory()() as db:
                row = db.scalar(select(m.SimState).limit(1))
                key = row.scenario_key if row else self.scenario_key
                scn = self.risk.load(db, key)
                self.scenario_key = key
                self.t = scn.clamp_t(scn.t_of(row.sim_time)) if row else float(scn.t_min)
                self.speed = row.speed if row else 1.0
        except Exception as exc:
            log.warning("sim restore without DB: %s", exc)
            scn = self.risk.load(None, self.scenario_key)
            self.t = float(scn.t_min)
        self.playing = False
        self._hour = self.risk.hour_index(self.t)

    # -- controls -------------------------------------------------------------

    async def _emit(self, force_risk: bool = False) -> None:
        await self.hub.publish("sim.tick", self.state())
        hour = self.risk.hour_index(self.t)
        if force_risk or hour != self._hour:
            prev = None if force_risk else self._hour
            self._hour = hour
            changed = self.risk.changed(prev, hour)
            await self.hub.publish(
                "risk.updated",
                {"t": hour, "areas": changed, "early_warning": self.risk.latest(hour)["early_warning"]},
            )

    async def play(self) -> dict[str, Any]:
        scn = self.risk.scenario
        if scn and self.t >= scn.t_max:
            self.t = float(scn.t_min)
        self.playing = True
        self._persist()
        await self._emit()
        return self.state()

    async def pause(self) -> dict[str, Any]:
        self.playing = False
        self._persist()
        await self._emit()
        return self.state()

    async def seek(self, t_hours: float) -> dict[str, Any]:
        assert self.risk.scenario is not None
        self.t = self.risk.scenario.clamp_t(t_hours)
        self._persist()
        await self._emit()
        return self.state()

    async def set_speed(self, speed: float) -> dict[str, Any]:
        if speed not in SPEEDS:
            raise ValueError(f"speed must be one of {SPEEDS}")
        self.speed = speed
        self._persist()
        await self._emit()
        return self.state()

    async def set_scenario(self, key: str) -> dict[str, Any]:
        with session_factory()() as db:
            scn = self.risk.load(db, key)
        self.scenario_key = key
        self.t = float(scn.t_min)
        self.playing = False
        self._persist()
        await self._emit(force_risk=True)
        return self.state()

    # -- ticker ---------------------------------------------------------------

    def advance(self, dt_real_s: float) -> None:
        scn = self.risk.scenario
        if not self.playing or scn is None:
            return
        self.t += dt_real_s * self.speed / get_settings().sim_seconds_per_hour
        if self.t >= scn.t_max:
            self.t = float(scn.t_max)
            self.playing = False

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        last = loop.time()
        persisted_hour = self._hour
        while True:
            await asyncio.sleep(TICK_S)
            now = loop.time()
            if self.playing:
                async with self._lock:
                    self.advance(now - last)
                    await self._emit()
                    if self._hour != persisted_hour or not self.playing:
                        persisted_hour = self._hour
                        self._persist()
            last = now

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
