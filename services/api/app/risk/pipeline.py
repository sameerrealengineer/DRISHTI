"""Scenario → engine inputs → scores + 12 h forecast (PRD §6.4, §6.5).

Pure: takes a Scenario, Geography and config; returns results. The API persists
them; the back-test harness consumes them directly.

Forecast inputs (BE-FC-1) for t+1..t+12:
  * rain        – the scenario's rain at t+h, standing in for the forecast product
  * river level – nowcast v1 from the level observed at t
  * wind        – from the cyclone track forecast at t+h
  * satellite   – persistence (flood fraction observed at t)
  * reports     – only reports known at t, ageing out of the 6 h window
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.forecast.nowcast import nowcast_level
from app.geo.static import Block, Geography
from app.reports.triage import analyze_report
from app.risk.engine import (
    DEFAULT_CONFIG,
    AreaInputs,
    ReportSignal,
    RiskResult,
    cyclone_wind_kmh,
    haversine_km,
    score_area,
)
from app.sim.scenario import Scenario

FORECAST_H = 12
DEFAULT_WIND_KMH = 15.0


@dataclass(frozen=True)
class TimedSignal:
    t: float
    signal: ReportSignal


@dataclass
class AreaRisk:
    block_id: str
    t: float
    result: RiskResult
    forecast: list[int]
    forecast_max_12h: int
    hours_to_severe: int | None
    inputs: dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> int:
        return self.result.score

    @property
    def level(self) -> str:
        return self.result.level

    def as_dict(self) -> dict[str, Any]:
        d = self.result.as_dict()
        d.update(
            area=self.block_id,
            t=self.t,
            forecast=self.forecast,
            forecast_max_12h=self.forecast_max_12h,
            hours_to_severe=self.hours_to_severe,
            inputs=self.inputs,
        )
        return d


def scenario_report_signals(scn: Scenario, geo: Geography) -> dict[str, list[TimedSignal]]:
    """Triage the scenario's timed citizen reports once (v1 rules) and bucket by block."""
    out: dict[str, list[TimedSignal]] = {}
    for r in scn.reports:
        tri = analyze_report(r.text, geo.place_names, geo.aliases)
        block = r.area or tri.place
        if not block:
            continue
        out.setdefault(block, []).append(
            TimedSignal(r.t, ReportSignal(tri.severity, tri.confidence, "UNVERIFIED"))
        )
    return out


def _wind(scn: Scenario, b: Block, t: float, vals: dict[str, float]) -> float:
    base = vals.get("wind_kmh", DEFAULT_WIND_KMH)
    c = scn.cyclone_at(t)
    if c is None:
        return base
    return max(base, cyclone_wind_kmh(c.vmax_kmh, haversine_km(b.lat, b.lon, c.lat, c.lon)))


def _reports_in_window(
    signals: list[TimedSignal], t_eval: float, known_at: float, window_h: float
) -> tuple[ReportSignal, ...]:
    return tuple(s.signal for s in signals if s.t <= known_at and t_eval - window_h < s.t <= t_eval)


class ScenarioScorer:
    """Scores every block at any scenario hour, with forecast. Caches per hour."""

    def __init__(
        self,
        scn: Scenario,
        geo: Geography,
        config: dict[str, Any] | None = None,
        extra_signals: dict[str, list[TimedSignal]] | None = None,
    ) -> None:
        self.scn = scn
        self.geo = geo
        self.cfg = config or DEFAULT_CONFIG
        self.signals = scenario_report_signals(scn, geo)
        for bid, sigs in (extra_signals or {}).items():
            self.signals.setdefault(bid, []).extend(sigs)
        self._cache: dict[tuple[str, int], AreaRisk] = {}

    # -- inputs ---------------------------------------------------------------

    def catchment_rain(self, gauge_id: str):
        blocks = self.geo.catchment(gauge_id)

        def rain(tau: int) -> float:
            vals = [self.scn.area_values(b.id, self.scn.clamp_t(tau)).get("rain_1h_mm", 0.0) for b in blocks]
            return sum(vals) / len(vals) if vals else 0.0

        return rain

    def inputs(
        self,
        b: Block,
        t_eval: float,
        known_at: float | None = None,
    ) -> AreaInputs:
        """Inputs at t_eval. If known_at < t_eval this is a forecast made at known_at."""
        known = t_eval if known_at is None else known_at
        is_fc = known < t_eval
        vals = self.scn.area_values(b.id, self.scn.clamp_t(t_eval))
        now_vals = self.scn.area_values(b.id, self.scn.clamp_t(known)) if is_fc else vals

        level = danger = None
        river_name = b.river
        g = self.geo.gauges.get(b.gauge) if b.gauge else None
        if g is not None:
            danger = g.danger_level_m
            river_name = g.river
            observed = self.scn.gauge_level(g.river, self.scn.clamp_t(known))
            if observed is not None:
                if is_fc:
                    h = int(round(t_eval - known))
                    level = nowcast_level(
                        observed,
                        self.catchment_rain(g.id),
                        int(known),
                        h,
                        g.nowcast_k,
                        (g.base_level_m, g.max_level_m),
                    )
                else:
                    level = observed

        return AreaInputs(
            rain_24h_mm=vals.get("rain_24h_mm", 0.0),
            river_level_m=level,
            danger_level_m=danger,
            river_name=river_name,
            flood_fraction=now_vals.get("flood_fraction", 0.0),  # persistence when forecasting
            wind_kmh=_wind(self.scn, b, t_eval, vals),
            elevation_m=b.elevation_m,
            coast_km=b.coast_km,
            kutcha_share=b.kutcha_share,
            population=b.population,
            reports=_reports_in_window(
                self.signals.get(b.id, []), t_eval, known, self.cfg["norms"]["report_window_h"]
            ),
        )

    # -- scoring --------------------------------------------------------------

    def area(self, block_id: str, t: int) -> AreaRisk:
        key = (block_id, t)
        if key in self._cache:
            return self._cache[key]
        b = self.geo.blocks[block_id]
        inp = self.inputs(b, t)
        res = score_area(inp, self.cfg)
        severe = self.cfg["thresholds"]["severe"]
        forecast = [
            score_area(self.inputs(b, t + h, known_at=t), self.cfg).score for h in range(1, FORECAST_H + 1)
        ]
        hts = next((h for h, s in enumerate(forecast, start=1) if s >= severe), None)
        ar = AreaRisk(
            block_id=block_id,
            t=t,
            result=res,
            forecast=forecast,
            forecast_max_12h=max(forecast),
            hours_to_severe=hts,
            inputs={
                "rain_24h_mm": round(inp.rain_24h_mm, 1),
                "river_level_m": None if inp.river_level_m is None else round(inp.river_level_m, 2),
                "danger_level_m": inp.danger_level_m,
                "river": inp.river_name,
                "flood_fraction": round(inp.flood_fraction, 3),
                "wind_kmh": round(inp.wind_kmh, 1),
                "reports": len(inp.reports),
            },
        )
        self._cache[key] = ar
        return ar

    def hour(self, t: int) -> dict[str, AreaRisk]:
        return {bid: self.area(bid, t) for bid in self.geo.blocks}


def early_warning_kpi(hour: dict[str, AreaRisk], geo: Geography, cfg: dict[str, Any] | None = None) -> dict:
    """BE-FC-3: "NOW" if any area Severe; else the area with the earliest hours-to-severe; else "Clear"."""
    c = cfg or DEFAULT_CONFIG
    severe = [a for a in hour.values() if a.score >= c["thresholds"]["severe"]]
    if severe:
        top = max(severe, key=lambda a: a.score)
        return {"state": "NOW", "area": top.block_id, "name": geo.blocks[top.block_id].name, "hours": 0}
    # Earliest hours-to-severe across all areas (BE-FC-3). Alert drafting uses the
    # narrower early_warning_candidates() list (BE-FC-2: current score below High).
    upcoming = [a for a in hour.values() if a.hours_to_severe is not None]
    if upcoming:
        first = min(upcoming, key=lambda a: (a.hours_to_severe, -a.score))
        return {
            "state": "WARNING",
            "area": first.block_id,
            "name": geo.blocks[first.block_id].name,
            "hours": first.hours_to_severe,
        }
    return {"state": "Clear", "area": None, "name": None, "hours": None}


def early_warning_candidates(hour: dict[str, AreaRisk], cfg: dict[str, Any] | None = None) -> list[AreaRisk]:
    """BE-FC-2: hours_to_severe in 1..12 and current score below High."""
    c = cfg or DEFAULT_CONFIG
    return [
        a
        for a in hour.values()
        if a.hours_to_severe is not None
        and 1 <= a.hours_to_severe <= 12
        and a.score < c["thresholds"]["high"]
    ]
