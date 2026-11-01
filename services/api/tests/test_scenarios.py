"""M2 Definition of Done: replay reproduces the reference prototype numbers."""

import json

import pytest

from app.config import get_settings
from app.forecast.nowcast import fit_k, nowcast_level
from app.geo.static import load_geography
from app.risk.backtest import run_backtest, to_markdown
from app.risk.pipeline import ScenarioScorer, early_warning_candidates, early_warning_kpi
from app.sim.scenario import list_scenarios, load_scenario

SEED = get_settings().seed_dir


@pytest.fixture(scope="module")
def geo():
    return load_geography(SEED)


@pytest.fixture(scope="module")
def titli(geo):
    return ScenarioScorer(load_scenario(SEED / "scenarios" / "titli.json"), geo)


@pytest.fixture(scope="module")
def phailin(geo):
    return ScenarioScorer(load_scenario(SEED / "scenarios" / "phailin.json"), geo)


@pytest.mark.parametrize(
    "block,expected",
    [("purushottampur", 83), ("patrapur", 82), ("chikiti", 72), ("sanakhemundi", 70), ("aska", 64)],
)
def test_titli_landfall_scores(titli, block, expected):
    assert abs(titli.area(block, 0).score - expected) <= 1


def test_phailin_landfall_ganjam(phailin):
    assert phailin.area("ganjam", 0).score >= 95


def test_scenarios_cover_all_blocks_and_hours(geo):
    for key, path in list_scenarios(SEED).items():
        scn = load_scenario(path)
        assert scn.hours == list(range(-24, 25)), key
        assert set(scn.areas) == set(geo.blocks), key
        for bid, series in scn.areas.items():
            assert set(series) == set(scn.hours), (key, bid)
        assert all(r.t >= -6 for r in scn.reports), key


def test_cyclone_track_interpolates(titli):
    scn = titli.scn
    c = scn.cyclone_at(-6)
    a, b = scn.track[1], scn.track[2]  # t=-12 and t=0
    assert c.lat == pytest.approx((a.lat + b.lat) / 2)
    assert scn.cyclone_at(99) is None


def test_rushikulya_peaks_after_landfall(titli):
    levels = {t: titli.scn.gauge_level("Rushikulya", t) for t in range(-24, 25)}
    peak_t = max(levels, key=levels.get)
    assert peak_t > 0  # "the wind left, the flood came"
    assert levels[peak_t] == pytest.approx(18.6, abs=0.05)


def test_early_warning_before_severe(titli, geo):
    # BE-FC-3: KPI names the area with the earliest hours-to-severe, before it turns Severe.
    kpi = early_warning_kpi(titli.hour(-7), geo)
    assert kpi["state"] == "WARNING"
    assert kpi["name"] == "Purushottampur"
    assert kpi["hours"] == 12
    assert titli.area("purushottampur", -7).score < 75
    # BE-FC-2: alert-draft candidates are below High now but forecast Severe within 12 h.
    cands = early_warning_candidates(titli.hour(-4))
    assert [a.block_id for a in cands] == ["patrapur"]
    assert all(a.score < 55 and 1 <= a.hours_to_severe <= 12 for a in cands)
    assert early_warning_kpi(titli.hour(0), geo)["state"] == "NOW"


def test_forecast_fields(titli):
    a = titli.area("purushottampur", -8)
    assert len(a.forecast) == 12
    assert a.forecast_max_12h == max(a.forecast)
    if a.hours_to_severe is not None:
        assert a.forecast[a.hours_to_severe - 1] >= 75


def test_normal_day_stays_low(geo):
    sc = ScenarioScorer(load_scenario(SEED / "scenarios" / "normal.json"), geo)
    assert all(a.level == "Low" for t in range(-24, 25, 6) for a in sc.hour(t).values())


def test_nowcast():
    assert nowcast_level(10.0, lambda _t: 2.0, t=0, h=3, k=0.1, bounds=(5, 20)) == pytest.approx(10.6)
    assert nowcast_level(19.9, lambda _t: 50.0, t=0, h=12, k=0.1, bounds=(5, 20)) == 20
    rain = [1.0] * 40
    levels = [10 + 0.05 * i for i in range(40)]  # +0.05 m/h with 1 mm/h -> k=0.05
    assert fit_k(levels, rain) == pytest.approx(0.05)


def test_backtest_titli(geo):
    truth = json.loads((SEED / "scenarios" / "titli.ground_truth.json").read_text())
    res = run_backtest(load_scenario(SEED / "scenarios" / "titli.json"), geo, truth)
    assert res["truth_count"] == 13
    assert 0 <= res["recall"] <= 1
    assert res["recall"] >= 0.8
    assert res["false_alarm_rate"] <= 0.25
    assert "Back-test" in to_markdown(res)
