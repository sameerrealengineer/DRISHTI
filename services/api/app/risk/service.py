"""Risk service: runs the pure pipeline for the active scenario and persists results.

In DEMO mode the whole replay (-24..+24 h) is scored when a scenario is loaded
and written to `risk_score` (history, district curve, back-tests). "Latest"
means the hour of the sim clock.
"""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models as m
from app.config import get_settings
from app.geo.static import Geography, default_geography
from app.risk.engine import DEFAULT_CONFIG, merged_config
from app.risk.pipeline import AreaRisk, ScenarioScorer, early_warning_candidates, early_warning_kpi
from app.sim.scenario import Scenario, list_scenarios, load_scenario


def active_config(db: Session) -> dict[str, Any]:
    row = db.scalar(
        select(m.RiskConfig).where(m.RiskConfig.active.is_(True)).order_by(m.RiskConfig.version.desc())
    )
    if row is None:
        return DEFAULT_CONFIG
    return merged_config({"version": row.version, **row.weights, "thresholds": row.thresholds})


class RiskService:
    def __init__(self, geo: Geography | None = None) -> None:
        self.geo = geo or default_geography()
        self.scenario: Scenario | None = None
        self.scorer: ScenarioScorer | None = None
        self.config: dict[str, Any] = DEFAULT_CONFIG

    def load(self, db: Session | None, key: str) -> Scenario:
        paths = list_scenarios(get_settings().seed_dir)
        if key not in paths:
            raise KeyError(key)
        self.scenario = load_scenario(paths[key])
        self.config = active_config(db) if db is not None else DEFAULT_CONFIG
        self.scorer = ScenarioScorer(self.scenario, self.geo, self.config)
        if db is not None:
            self.materialize(db)
        return self.scenario

    def hour_index(self, t: float) -> int:
        assert self.scenario is not None
        return int(max(self.scenario.t_min, min(self.scenario.t_max, math.floor(t))))

    def hour(self, t: float) -> dict[str, AreaRisk]:
        assert self.scorer is not None
        return self.scorer.hour(self.hour_index(t))

    def materialize(self, db: Session) -> int:
        """Score every hour of the replay and store it in risk_score."""
        assert self.scenario is not None and self.scorer is not None
        scn_row = db.scalar(select(m.Scenario).where(m.Scenario.key == self.scenario.key))
        area_ids = dict(db.execute(select(m.Area.code, m.Area.id).where(m.Area.kind == "block")).all())
        if scn_row is None or not area_ids:
            return 0
        db.execute(
            delete(m.RiskScore).where(m.RiskScore.scenario_id == scn_row.id, m.RiskScore.mode == "demo")
        )
        rows = []
        for t in range(self.scenario.t_min, self.scenario.t_max + 1):
            for code, ar in self.scorer.hour(t).items():
                if code not in area_ids:
                    continue
                r = ar.result
                rows.append(
                    dict(
                        area_id=area_ids[code],
                        at=self.scenario.sim_time(t),
                        score=r.score,
                        level=r.level,
                        hazard=r.hazard,
                        exposure=r.exposure,
                        vulnerability=r.vulnerability,
                        citizen=r.citizen,
                        components=r.components,
                        drivers=r.drivers,
                        contributions=r.contributions,
                        forecast_max_12h=ar.forecast_max_12h,
                        hours_to_severe=ar.hours_to_severe,
                        config_version=r.config_version,
                        mode="demo",
                        scenario_id=scn_row.id,
                    )
                )
        db.execute(m.RiskScore.__table__.insert(), rows)
        db.commit()
        return len(rows)

    # -- views ------------------------------------------------------------------

    def area_view(self, ar: AreaRisk) -> dict[str, Any]:
        b = self.geo.blocks[ar.block_id]
        d = ar.as_dict()
        d.update(code=b.id, name=b.name, name_or=b.name_or)
        return d

    def latest(self, t: float) -> dict[str, Any]:
        hour = self.hour(t)
        items = sorted((self.area_view(a) for a in hour.values()), key=lambda x: -x["score"])
        return {
            "t": self.hour_index(t),
            "at": self.scenario.sim_time(self.hour_index(t)).isoformat() if self.scenario else None,
            "config_version": self.config.get("version", 1),
            "areas": items,
            "early_warning": early_warning_kpi(hour, self.geo, self.config),
            "early_warning_candidates": [a.block_id for a in early_warning_candidates(hour, self.config)],
            "counts": {
                lv: sum(1 for a in hour.values() if a.level == lv)
                for lv in ("Severe", "High", "Moderate", "Low")
            },
        }

    def changed(self, t_prev: int | None, t_new: int) -> list[dict[str, Any]]:
        """Areas whose score/level/HTS differ between two hours (for risk.updated)."""
        new = self.hour(t_new)
        if t_prev is None:
            return [self._slim(a) for a in new.values()]
        old = self.hour(t_prev)
        out = []
        for bid, a in new.items():
            o = old.get(bid)
            if o is None or (o.score, o.level, o.hours_to_severe) != (a.score, a.level, a.hours_to_severe):
                out.append(self._slim(a))
        return out

    def _slim(self, a: AreaRisk) -> dict[str, Any]:
        return {
            "code": a.block_id,
            "score": a.score,
            "level": a.level,
            "forecast_max_12h": a.forecast_max_12h,
            "hours_to_severe": a.hours_to_severe,
            "drivers": a.result.drivers,
        }

    def district_curve(self) -> dict[str, Any]:
        assert self.scenario is not None and self.scorer is not None
        pts = []
        for t in range(self.scenario.t_min, self.scenario.t_max + 1):
            hour = self.scorer.hour(t)
            scores = [a.score for a in hour.values()]
            top = max(hour.values(), key=lambda a: a.score)
            pts.append(
                {
                    "t": t,
                    "at": self.scenario.sim_time(t).isoformat(),
                    "max": max(scores),
                    "mean": round(sum(scores) / len(scores), 1),
                    "max_area": top.block_id,
                }
            )
        return {"scenario": self.scenario.key, "points": pts}

    def area_history(self, code: str) -> list[dict[str, Any]]:
        assert self.scenario is not None and self.scorer is not None
        return [
            {"t": t, "score": self.scorer.area(code, t).score, "level": self.scorer.area(code, t).level}
            for t in range(self.scenario.t_min, self.scenario.t_max + 1)
        ]

    def gauges(self, t: float) -> list[dict[str, Any]]:
        assert self.scenario is not None
        ti = self.hour_index(t)
        out = []
        for g in self.geo.gauges.values():
            level = self.scenario.gauge_level(g.river, ti)
            out.append(
                {
                    "code": g.id,
                    "name": g.name,
                    "river": g.river,
                    "site": g.site,
                    "lat": g.lat,
                    "lon": g.lon,
                    "danger_level_m": g.danger_level_m,
                    "warning_level_m": g.warning_level_m,
                    "level_m": level,
                    "pct_of_danger": None if level is None else round(100 * level / g.danger_level_m, 1),
                    "status": None
                    if level is None
                    else (
                        "danger"
                        if level >= g.danger_level_m
                        else "warning"
                        if level >= g.warning_level_m
                        else "normal"
                    ),
                }
            )
        return out

    def gauge_readings(self, code: str, t: float) -> list[dict[str, Any]]:
        assert self.scenario is not None
        g = self.geo.gauges[code]
        ti = self.hour_index(t)
        return [
            {
                "t": h,
                "at": self.scenario.sim_time(h).isoformat(),
                "level_m": self.scenario.gauge_level(g.river, h),
            }
            for h in range(max(self.scenario.t_min, ti - 24), ti + 1)
        ]

    def cyclone(self, t: float) -> dict[str, Any] | None:
        assert self.scenario is not None
        if not self.scenario.track:
            return None
        now = self.scenario.cyclone_at(t)
        return {
            "name": self.scenario.cyclone_name,
            "now": None if now is None else {"lat": now.lat, "lon": now.lon, "vmax_kmh": round(now.vmax_kmh)},
            "hours_to_landfall": round(-t, 1) if t < 0 else 0,
            "track": [
                {"t": p.t, "lat": p.lat, "lon": p.lon, "vmax_kmh": p.vmax_kmh, "is_forecast": p.t > t}
                for p in self.scenario.track
            ],
        }


risk_service = RiskService()
