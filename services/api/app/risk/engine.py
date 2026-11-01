"""Risk fusion engine — PRD §6.4.

Pure and deterministic: no I/O, no clock. All weights/thresholds come from a
config dict (versioned in `risk_config`; defaults below).

    rainS  = clamp(rain_24h / 220)
    riverS = clamp((level/danger - 0.75) / 0.35)
    satS   = clamp(flood_fraction / 0.25)
    windS  = clamp((wind - 50) / 130)
    Hazard = clamp(0.30 rainS + 0.25 riverS + 0.25 satS + 0.20 windS + 0.25 top1 top2)
    Exposure = 0.6 clamp((80 - elevation)/80) + 0.4 exp(-coast_km/22)
    Vulnerability = 0.6 clamp((kutcha - 0.30)/0.25) + 0.4 clamp(population/170000)
    Citizen = clamp(sum(severity/5 * confidence * status_weight) / 1.5)
    Risk = round(100 clamp(H (0.55 + 0.45 E)(0.8 + 0.2 V) + 0.18 C))
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "weights": {
        "rain": 0.30,
        "river": 0.25,
        "sat": 0.25,
        "wind": 0.20,
        "synergy": 0.25,
        "exposure_base": 0.55,
        "exposure_gain": 0.45,
        "vuln_base": 0.8,
        "vuln_gain": 0.2,
        "citizen": 0.18,
        "exp_elevation": 0.6,
        "exp_coast": 0.4,
        "vul_kutcha": 0.6,
        "vul_population": 0.4,
    },
    "norms": {
        "rain_mm": 220.0,
        "river_ratio_floor": 0.75,
        "river_ratio_span": 0.35,
        "flood_fraction": 0.25,
        "wind_floor_kmh": 50.0,
        "wind_span_kmh": 130.0,
        "elevation_ref_m": 80.0,
        "coast_decay_km": 22.0,
        "kutcha_floor": 0.30,
        "kutcha_span": 0.25,
        "population_ref": 170000.0,
        "citizen_norm": 1.5,
        "report_window_h": 6.0,
    },
    # Weight of a citizen report in the Citizen term by status. Duplicates count 0
    # because their parent report already carries the signal.
    "report_weights": {"VERIFIED": 1.0, "UNVERIFIED": 0.6, "REJECTED": 0.0, "DUPLICATE": 0.0},
    "thresholds": {"severe": 75, "high": 55, "moderate": 30},
}

LEVELS = ("Low", "Moderate", "High", "Severe")
CONTRIBUTION_KEYS = ("Rainfall", "River", "Satellite", "Wind", "Citizens")


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def merged_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    for key, val in (overrides or {}).items():
        if isinstance(val, dict) and isinstance(cfg.get(key), dict):
            cfg[key].update(val)
        else:
            cfg[key] = val
    return cfg


@dataclass(frozen=True)
class ReportSignal:
    severity: int  # 1..5
    confidence: float  # 0..1
    status: str = "UNVERIFIED"  # VERIFIED | UNVERIFIED | REJECTED | DUPLICATE


@dataclass(frozen=True)
class AreaInputs:
    rain_24h_mm: float = 0.0
    river_level_m: float | None = None
    danger_level_m: float | None = None
    river_name: str | None = None
    flood_fraction: float = 0.0
    wind_kmh: float = 0.0
    elevation_m: float = 50.0
    coast_km: float = 50.0
    kutcha_share: float = 0.3
    population: float = 100000.0
    reports: tuple[ReportSignal, ...] = field(default_factory=tuple)


@dataclass
class RiskResult:
    score: int
    level: str
    hazard: float
    exposure: float
    vulnerability: float
    citizen: float
    components: dict[str, float]
    contributions: dict[str, float]
    drivers: list[str]
    config_version: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "hazard": round(self.hazard, 4),
            "exposure": round(self.exposure, 4),
            "vulnerability": round(self.vulnerability, 4),
            "citizen": round(self.citizen, 4),
            "components": {k: round(v, 4) for k, v in self.components.items()},
            "contributions": self.contributions,
            "drivers": self.drivers,
            "config_version": self.config_version,
        }


def level_for(score: float, cfg: dict[str, Any] | None = None) -> str:
    th = (cfg or DEFAULT_CONFIG)["thresholds"]
    if score >= th["severe"]:
        return "Severe"
    if score >= th["high"]:
        return "High"
    if score >= th["moderate"]:
        return "Moderate"
    return "Low"


def cyclone_wind_kmh(vmax_kmh: float, distance_km: float) -> float:
    """BE-RISK-3: wind at an area from the cyclone centre."""
    return max(25.0, vmax_kmh * math.exp(-distance_km / 95.0))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def hazard_components(inp: AreaInputs, cfg: dict[str, Any]) -> dict[str, float]:
    n = cfg["norms"]
    rain_s = clamp(inp.rain_24h_mm / n["rain_mm"])
    if inp.river_level_m is not None and inp.danger_level_m:
        ratio = inp.river_level_m / inp.danger_level_m
        river_s = clamp((ratio - n["river_ratio_floor"]) / n["river_ratio_span"])
    else:
        river_s = 0.0
    sat_s = clamp(inp.flood_fraction / n["flood_fraction"])
    wind_s = clamp((inp.wind_kmh - n["wind_floor_kmh"]) / n["wind_span_kmh"])
    return {"rain": rain_s, "river": river_s, "sat": sat_s, "wind": wind_s}


def citizen_signal(reports: tuple[ReportSignal, ...] | list[ReportSignal], cfg: dict[str, Any]) -> float:
    rw = cfg["report_weights"]
    total = sum(
        (clamp(r.severity, 1, 5) / 5.0) * clamp(r.confidence) * rw.get(r.status.upper(), rw["UNVERIFIED"])
        for r in reports
    )
    return clamp(total / cfg["norms"]["citizen_norm"])


def score_area(inp: AreaInputs, config: dict[str, Any] | None = None) -> RiskResult:
    cfg = config or DEFAULT_CONFIG
    w, n = cfg["weights"], cfg["norms"]

    comp = hazard_components(inp, cfg)
    ordered = sorted(comp.values(), reverse=True)
    top1, top2 = ordered[0], ordered[1]
    linear = {
        "rain": w["rain"] * comp["rain"],
        "river": w["river"] * comp["river"],
        "sat": w["sat"] * comp["sat"],
        "wind": w["wind"] * comp["wind"],
    }
    synergy = w["synergy"] * top1 * top2
    hazard_raw = sum(linear.values()) + synergy
    hazard = clamp(hazard_raw)

    exposure = w["exp_elevation"] * clamp(
        (n["elevation_ref_m"] - inp.elevation_m) / n["elevation_ref_m"]
    ) + w["exp_coast"] * math.exp(-inp.coast_km / n["coast_decay_km"])
    vulnerability = w["vul_kutcha"] * clamp((inp.kutcha_share - n["kutcha_floor"]) / n["kutcha_span"]) + w[
        "vul_population"
    ] * clamp(inp.population / n["population_ref"])
    citizen = citizen_signal(inp.reports, cfg)

    multiplier = (w["exposure_base"] + w["exposure_gain"] * exposure) * (
        w["vuln_base"] + w["vuln_gain"] * vulnerability
    )
    raw = hazard * multiplier + w["citizen"] * citizen
    score = round(100 * clamp(raw))
    level = level_for(score, cfg)

    contributions = _contributions(
        comp, linear, synergy, hazard_raw, hazard, multiplier, w["citizen"] * citizen
    )
    drivers = _drivers(inp, comp, contributions)

    return RiskResult(
        score=score,
        level=level,
        hazard=hazard,
        exposure=exposure,
        vulnerability=vulnerability,
        citizen=citizen,
        components=comp,
        contributions=contributions,
        drivers=drivers,
        config_version=int(cfg.get("version", 1)),
    )


def _contributions(
    comp: dict[str, float],
    linear: dict[str, float],
    synergy: float,
    hazard_raw: float,
    hazard: float,
    multiplier: float,
    citizen_part: float,
) -> dict[str, float]:
    """Split the score into points per source (BE-RISK-2 contribution bars).

    The synergy term is shared between the two largest components in proportion
    to their values. Hazard clamping and the final clamp at 100 are spread
    proportionally so the bars add up to the score.
    """
    share = dict(linear)
    top = sorted(comp, key=lambda k: comp[k], reverse=True)[:2]
    denom = comp[top[0]] + comp[top[1]]
    if synergy > 0 and denom > 0:
        for k in top:
            share[k] += synergy * comp[k] / denom
    scale = (hazard / hazard_raw) if hazard_raw > 0 else 0.0
    pts = {
        "Rainfall": 100 * share["rain"] * scale * multiplier,
        "River": 100 * share["river"] * scale * multiplier,
        "Satellite": 100 * share["sat"] * scale * multiplier,
        "Wind": 100 * share["wind"] * scale * multiplier,
        "Citizens": 100 * citizen_part,
    }
    total = sum(pts.values())
    if total > 100:
        pts = {k: v * 100 / total for k, v in pts.items()}
    return {k: round(v, 1) for k, v in pts.items()}


def _drivers(inp: AreaInputs, comp: dict[str, float], contributions: dict[str, float]) -> list[str]:
    text = {
        "Rainfall": f"Rain {round(inp.rain_24h_mm)} mm",
        "River": (
            f"{inp.river_name or 'River'} {round(100 * inp.river_level_m / inp.danger_level_m)}% of danger"
            if inp.river_level_m is not None and inp.danger_level_m
            else ""
        ),
        "Satellite": f"Satellite water {round(100 * inp.flood_fraction)}%",
        "Wind": f"Wind {round(inp.wind_kmh)} km/h",
        "Citizens": f"{len(inp.reports)} citizen report{'s' if len(inp.reports) != 1 else ''}",
    }
    ranked = sorted(
        (k for k in CONTRIBUTION_KEYS if contributions[k] >= 1.0 and text[k]),
        key=lambda k: contributions[k],
        reverse=True,
    )
    return [text[k] for k in ranked[:3]]
