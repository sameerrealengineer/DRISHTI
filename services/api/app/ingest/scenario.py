"""Scenario adapters (DEMO mode): read the active replay instead of live feeds."""

from __future__ import annotations

from app.ingest.base import Adapter, Observation, Window, register
from app.sim.scenario import Scenario


class _ScenarioAdapter(Adapter):
    kind = "scenario"

    def __init__(self, scenario: Scenario) -> None:
        self.scn = scenario

    def _hours(self, window: Window) -> range:
        lo = max(self.scn.t_min, int(self.scn.t_of(window.start)))
        hi = min(self.scn.t_max, int(self.scn.t_of(window.end)))
        return range(lo, hi + 1)


@register
class ScenarioWeather(_ScenarioAdapter):
    source = "weather"

    def fetch(self, window: Window) -> list[Observation]:
        out = []
        for t in self._hours(window):
            for code in self.scn.areas:
                v = self.scn.area_values(code, t)
                out.append(
                    Observation(
                        "weather", code, self.scn.sim_time(t), {"precip_mm": v.get("rain_1h_mm", 0.0)}
                    )
                )
        return out


@register
class ScenarioGauges(_ScenarioAdapter):
    source = "gauges"

    def fetch(self, window: Window) -> list[Observation]:
        return [
            Observation("gauges", river, self.scn.sim_time(t), {"level_m": self.scn.gauge_level(river, t)})
            for t in self._hours(window)
            for river in self.scn.gauges
        ]


@register
class ScenarioSatellite(_ScenarioAdapter):
    source = "satellite"

    def fetch(self, window: Window) -> list[Observation]:
        return [
            Observation(
                "satellite",
                code,
                self.scn.sim_time(t),
                {"flood_fraction": self.scn.area_values(code, t).get("flood_fraction", 0.0)},
            )
            for t in self._hours(window)
            for code in self.scn.areas
        ]
