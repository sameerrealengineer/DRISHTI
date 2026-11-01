"""Scenario files (PRD §12, Appendix 21.2) — hour-by-hour replay data.

    {
      "key": "titli", "name": ..., "landfall_at": "2018-10-11T05:00:00+05:30",
      "hours": [-24, ..., 24],
      "cyclone": {"name": "Titli", "track": [{"t": -24, "lat": .., "lon": .., "vmax_kmh": ..}]},
      "gauges": {"Rushikulya": [{"t": -24, "level_m": 9.8}, ...]},
      "areas": {"purushottampur": [{"t": -24, "rain_1h_mm": .., "rain_24h_mm": .., "flood_fraction": ..}]},
      "reports": [{"t": -3, "text": "...", "channel": "whatsapp", "area": "purushottampur"}]
    }

`t` is hours relative to landfall. Values between listed hours are taken from
the previous listed hour (step), except the cyclone track which is linearly
interpolated.
"""

from __future__ import annotations

import json
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrackPoint:
    t: float
    lat: float
    lon: float
    vmax_kmh: float


@dataclass(frozen=True)
class ScenarioReport:
    t: float
    text: str
    channel: str
    area: str | None
    lat: float | None = None
    lon: float | None = None


@dataclass
class Scenario:
    key: str
    name: str
    landfall_at: datetime
    note: str
    hours: list[int]
    cyclone_name: str | None
    track: list[TrackPoint]
    gauges: dict[str, dict[int, float]]  # river -> t -> level
    areas: dict[str, dict[int, dict[str, float]]]  # block -> t -> values
    reports: list[ScenarioReport] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def t_min(self) -> int:
        return self.hours[0]

    @property
    def t_max(self) -> int:
        return self.hours[-1]

    def sim_time(self, t_hours: float) -> datetime:
        return self.landfall_at + timedelta(hours=t_hours)

    def t_of(self, when: datetime) -> float:
        return (when - self.landfall_at).total_seconds() / 3600.0

    def clamp_t(self, t: float) -> float:
        return max(self.t_min, min(self.t_max, t))

    @staticmethod
    def _step(series: dict[int, Any], t: float) -> Any:
        keys = sorted(series)
        if not keys:
            return None
        i = bisect_right(keys, t) - 1
        return series[keys[max(0, i)]]

    def area_values(self, block_id: str, t: float) -> dict[str, float]:
        series = self.areas.get(block_id)
        return dict(self._step(series, t) or {}) if series else {}

    def gauge_level(self, river: str, t: float) -> float | None:
        series = self.gauges.get(river)
        return self._step(series, t) if series else None

    def cyclone_at(self, t: float) -> TrackPoint | None:
        if not self.track or t < self.track[0].t or t > self.track[-1].t:
            return None
        for a, b in zip(self.track, self.track[1:], strict=False):
            if a.t <= t <= b.t:
                f = 0.0 if b.t == a.t else (t - a.t) / (b.t - a.t)
                return TrackPoint(
                    t=t,
                    lat=a.lat + f * (b.lat - a.lat),
                    lon=a.lon + f * (b.lon - a.lon),
                    vmax_kmh=a.vmax_kmh + f * (b.vmax_kmh - a.vmax_kmh),
                )
        return self.track[-1]

    def summary(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "landfall_at": self.landfall_at.isoformat(),
            "note": self.note,
            "t_min": self.t_min,
            "t_max": self.t_max,
            "cyclone": self.cyclone_name,
        }


def parse_scenario(data: dict[str, Any]) -> Scenario:
    hours = [int(h) for h in data["hours"] if not isinstance(h, str)]
    cyc = data.get("cyclone") or {}
    track = [TrackPoint(p["t"], p["lat"], p["lon"], p["vmax_kmh"]) for p in cyc.get("track", [])]
    gauges = {
        river: {int(p["t"]): float(p["level_m"]) for p in pts}
        for river, pts in data.get("gauges", {}).items()
    }
    areas = {
        bid: {int(p["t"]): {k: float(v) for k, v in p.items() if k != "t"} for p in pts}
        for bid, pts in data.get("areas", {}).items()
    }
    reports = [
        ScenarioReport(
            t=float(r["t"]),
            text=r["text"],
            channel=r.get("channel", "app"),
            area=r.get("area"),
            lat=r.get("lat"),
            lon=r.get("lon"),
        )
        for r in data.get("reports", [])
    ]
    return Scenario(
        key=data["key"],
        name=data["name"],
        landfall_at=datetime.fromisoformat(data["landfall_at"]),
        note=data.get("note", ""),
        hours=sorted(hours),
        cyclone_name=cyc.get("name"),
        track=sorted(track, key=lambda p: p.t),
        gauges=gauges,
        areas=areas,
        reports=sorted(reports, key=lambda r: r.t),
        raw=data,
    )


def load_scenario(path: Path) -> Scenario:
    return parse_scenario(json.loads(path.read_text()))


def list_scenarios(seed_dir: Path) -> dict[str, Path]:
    return {
        p.stem: p
        for p in sorted((seed_dir / "scenarios").glob("*.json"))
        if not p.name.endswith(".ground_truth.json")
    }
