import math

import pytest

from app.risk.engine import (
    DEFAULT_CONFIG,
    AreaInputs,
    ReportSignal,
    clamp,
    cyclone_wind_kmh,
    level_for,
    merged_config,
    score_area,
)


def manual_score(inp: AreaInputs) -> int:
    """Independent re-implementation of the PRD §6.4 formula."""
    rain = clamp(inp.rain_24h_mm / 220)
    river = clamp((inp.river_level_m / inp.danger_level_m - 0.75) / 0.35) if inp.river_level_m else 0.0
    sat = clamp(inp.flood_fraction / 0.25)
    wind = clamp((inp.wind_kmh - 50) / 130)
    a, b = sorted([rain, river, sat, wind], reverse=True)[:2]
    hazard = clamp(0.30 * rain + 0.25 * river + 0.25 * sat + 0.20 * wind + 0.25 * a * b)
    exposure = 0.6 * clamp((80 - inp.elevation_m) / 80) + 0.4 * math.exp(-inp.coast_km / 22)
    vuln = 0.6 * clamp((inp.kutcha_share - 0.30) / 0.25) + 0.4 * clamp(inp.population / 170000)
    weights = {"VERIFIED": 1.0, "UNVERIFIED": 0.6, "REJECTED": 0.0, "DUPLICATE": 0.0}
    cit = clamp(sum(r.severity / 5 * r.confidence * weights[r.status] for r in inp.reports) / 1.5)
    return round(100 * clamp(hazard * (0.55 + 0.45 * exposure) * (0.8 + 0.2 * vuln) + 0.18 * cit))


CASES = [
    AreaInputs(),
    AreaInputs(
        rain_24h_mm=198,
        river_level_m=17.8,
        danger_level_m=16.83,
        flood_fraction=0.27,
        wind_kmh=150,
        elevation_m=24,
        coast_km=21.8,
        kutcha_share=0.5,
        population=132000,
        reports=(ReportSignal(5, 0.9), ReportSignal(4, 0.8, "VERIFIED")),
    ),
    AreaInputs(
        rain_24h_mm=40, river_level_m=10, danger_level_m=16.83, wind_kmh=30, elevation_m=120, coast_km=80
    ),
    AreaInputs(
        rain_24h_mm=500,
        river_level_m=25,
        danger_level_m=16.83,
        flood_fraction=0.9,
        wind_kmh=250,
        elevation_m=0,
        coast_km=0,
        kutcha_share=1,
        population=500000,
        reports=tuple(ReportSignal(5, 0.97, "VERIFIED") for _ in range(5)),
    ),
    AreaInputs(
        rain_24h_mm=120,
        flood_fraction=0.05,
        wind_kmh=90,
        elevation_m=40,
        coast_km=10,
        reports=(ReportSignal(3, 0.6, "REJECTED"), ReportSignal(5, 0.9, "DUPLICATE")),
    ),
]


@pytest.mark.parametrize("inp", CASES)
def test_score_matches_prd_formula(inp):
    assert score_area(inp).score == manual_score(inp)


def test_score_bounds_and_levels():
    assert score_area(CASES[0]).score == 0
    assert score_area(CASES[3]).score == 100
    assert score_area(CASES[3]).level == "Severe"
    assert [level_for(s) for s in (0, 29, 30, 54, 55, 74, 75, 100)] == [
        "Low",
        "Low",
        "Moderate",
        "Moderate",
        "High",
        "High",
        "Severe",
        "Severe",
    ]


def test_rejected_and_duplicate_reports_carry_no_weight():
    base = AreaInputs(rain_24h_mm=120, wind_kmh=90, elevation_m=40, coast_km=10)
    assert (
        score_area(CASES[4]).score
        == score_area(AreaInputs(**{**base.__dict__, "flood_fraction": 0.05})).score
    )


def test_verified_outweighs_unverified():
    base = dict(rain_24h_mm=100, elevation_m=30, coast_km=10)
    v = score_area(AreaInputs(**base, reports=(ReportSignal(5, 0.9, "VERIFIED"),)))
    u = score_area(AreaInputs(**base, reports=(ReportSignal(5, 0.9, "UNVERIFIED"),)))
    assert v.citizen == pytest.approx(0.6)
    assert u.citizen == pytest.approx(0.36)
    assert v.score > u.score


def test_citizen_signal_capped_at_18_points():
    """Responsible AI (§11.7): citizen reports alone can add at most 18 points."""
    many = tuple(ReportSignal(5, 0.97, "VERIFIED") for _ in range(20))
    res = score_area(AreaInputs(reports=many))
    assert res.score == 18
    assert res.contributions["Citizens"] == 18.0


def test_contributions_sum_to_score_and_drivers():
    res = score_area(CASES[1])
    assert sum(res.contributions.values()) == pytest.approx(res.score, abs=1.0)
    assert set(res.contributions) == {"Rainfall", "River", "Satellite", "Wind", "Citizens"}
    assert 1 <= len(res.drivers) <= 3
    joined = " ".join(res.drivers)
    assert "Rain 198 mm" in joined or "Wind 150 km/h" in joined or "106% of danger" in joined


def test_driver_strings_format():
    inp = AreaInputs(
        rain_24h_mm=198,
        river_level_m=17.84,
        danger_level_m=16.83,
        river_name="Rushikulya",
        flood_fraction=0.27,
        wind_kmh=150,
        elevation_m=10,
        coast_km=5,
    )
    res = score_area(inp)
    texts = set(res.drivers)
    assert texts <= {"Rain 198 mm", "Rushikulya 106% of danger", "Satellite water 27%", "Wind 150 km/h"}
    assert len(texts) == 3


def test_cyclone_wind():
    assert cyclone_wind_kmh(150, 0) == pytest.approx(150)
    assert cyclone_wind_kmh(150, 95) == pytest.approx(150 / math.e)
    assert cyclone_wind_kmh(150, 1000) == 25


def test_config_overrides_change_score():
    inp = CASES[1]
    cfg = merged_config({"version": 2, "weights": {"citizen": 0.0}})
    res = score_area(inp, cfg)
    assert res.config_version == 2
    assert res.score <= score_area(inp).score
    assert DEFAULT_CONFIG["weights"]["citizen"] == 0.18  # defaults untouched
