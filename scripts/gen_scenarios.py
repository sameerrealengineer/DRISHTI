"""Generate the demo scenarios: seed/scenarios/{titli,phailin,normal}.json (+ ground truth).

These are ILLUSTRATIVE RECONSTRUCTIONS, not observed data. The reference
prototype's scenario files were not available, so for Titli the peak rain of the
five blocks named in the PRD M2 Definition of Done gets its flood-onset hour
tuned (bisection; earlier onset = more satellite-detected water at landfall) until the
engine reproduces the reference scores at landfall (t=0):
Purushottampur 83, Patrapur 82, Chikiti 72, Sanakhemundi 70, Aska 64.
Gauge response constants are tuned so the Rushikulya @ Purushottampur peaks at
18.60 m (the level reported during Titli). Everything else is hand-set.

    cd services/api && uv run python ../../scripts/gen_scenarios.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.forecast.nowcast import fit_k  # noqa: E402
from app.geo.static import load_geography  # noqa: E402
from app.risk.pipeline import ScenarioScorer  # noqa: E402
from app.sim.scenario import parse_scenario  # noqa: E402

SEED = ROOT / "seed"
HOURS = list(range(-24, 25))
SPIN = 48  # hours of spin-up before -24 so 24 h rain totals are complete
RECESSION = 0.92

# block: (peak rain mm/h, t_peak, sigma_h, max flood fraction, t_flood)
TITLI = {
    "purushottampur": (15, -5, 8, 0.32, 6),
    "patrapur": (15, -5, 8, 0.30, 3),
    "chikiti": (15, -5, 8, 0.25, 3),
    "sanakhemundi": (15, -5, 8, 0.25, 5),
    "aska": (15, -5, 8, 0.25, 6),
    "ganjam": (13, -4, 8, 0.25, 6),
    "hinjilicut": (14, -5, 8, 0.20, 6),
    "kabisuryanagar": (14, -5, 8, 0.18, 6),
    "polasara": (12, -4, 8, 0.15, 7),
    "digapahandi": (14, -5, 8, 0.12, 5),
    "kukudakhandi": (12, -4, 7, 0.12, 4),
    "rangeilunda": (11, -4, 7, 0.10, 4),
    "chhatrapur": (10, -3, 7, 0.08, 5),
    "khallikote": (8, -2, 7, 0.06, 6),
    "beguniapada": (8, -2, 7, 0.06, 7),
    "buguda": (10, -3, 8, 0.08, 7),
    "sorada": (11, -3, 8, 0.10, 7),
    "sheragada": (10, -4, 8, 0.06, 6),
    "dharakote": (9, -3, 8, 0.05, 7),
    "bhanjanagar": (7, -2, 8, 0.04, 8),
    "bellaguntha": (7, -2, 8, 0.04, 8),
    "jagannathprasad": (8, -2, 8, 0.03, 8),
}
TITLI_TARGETS = {"purushottampur": 83, "patrapur": 82, "chikiti": 72, "sanakhemundi": 70, "aska": 64}
TITLI_GAUGE_PEAKS = {"Rushikulya": 18.60, "Bahuda": 9.40, "Ghodahada": 12.60, "Badanadi": 14.80}
TITLI_TRACK = [
    (-24, 17.80, 86.00, 130),
    (-12, 18.30, 85.20, 150),
    (0, 18.80, 84.45, 150),
    (6, 19.10, 84.20, 110),
    (12, 19.50, 84.15, 80),
    (18, 19.90, 84.30, 60),
    (24, 20.30, 84.60, 45),
]
TITLI_REPORTS = [
    (
        -3,
        "Rushikulya water entered our village near Purushottampur, waist deep, 30 families stuck on roof. Need boat",
        "whatsapp",
        "purushottampur",
    ),
    (
        -2,
        "Bahuda overflow near Patrapur, water knee deep inside houses, 12 families need help",
        "app",
        "patrapur",
    ),
    (-2, "Trees uprooted and huts collapsed in Chikiti, road cut off to the village", "sms", "chikiti"),
    (-2, "Sanakhemundi gaan re bonya pani, 6 families stuck on roof, help", "sms", "sanakhemundi"),
    (-1, "ସାନଖେମୁଣ୍ଡି ଗାଁରେ ବନ୍ୟା ପାଣି ଘରେ ପଶିଲାଣି", "whatsapp", "sanakhemundi"),
    (-1, "ପୁରୁଷୋତ୍ତମପୁର ପାଖରେ ବନ୍ୟା ପାଣି ଘରେ ପଶିଲା, ଲୋକ ଛାତ ଉପରେ", "whatsapp", "purushottampur"),
    (-1, "Aska mein paani bhar gaya, 20 log fase hain, bachao", "whatsapp", "aska"),
    (
        0,
        "Berhampur low roads flooded, electric pole fell near bus stand, power line down",
        "app",
        "kukudakhandi",
    ),
    (2, "Hinjili canal overflow, water waist deep, child missing, need boat", "whatsapp", "hinjilicut"),
    (
        4,
        "Bridge washed away near Purushottampur, our village is cut off, 8 families stranded",
        "app",
        "purushottampur",
    ),
    (5, "Digapahandi market inundated, elderly woman sick, need doctor", "sms", "digapahandi"),
    (
        8,
        "Rushikulya breach near Ganjam town, water entering houses, 40 people on school roof",
        "whatsapp",
        "ganjam",
    ),
    (10, "Polasara fields submerged, road cut off, food needed for 15 families", "app", "polasara"),
    (
        12,
        "Kabisuryanagar low wards flooded knee deep, people moved to shelter, need ration",
        "app",
        "kabisuryanagar",
    ),
]
TITLI_TRUTH = {
    "purushottampur": 8,
    "patrapur": 2,
    "chikiti": 2,
    "sanakhemundi": 4,
    "aska": 8,
    "ganjam": 10,
    "hinjilicut": 6,
    "kabisuryanagar": 8,
    "polasara": 10,
    "digapahandi": 4,
    "kukudakhandi": 3,
    "rangeilunda": 2,
    "sorada": 10,
}

PHAILIN = {
    "ganjam": (22, -2, 5, 0.35, -2),
    "chhatrapur": (19, -2, 5, 0.30, -1),
    "rangeilunda": (18, -2, 5, 0.25, -1),
    "khallikote": (17, 0, 5, 0.25, 2),
    "kukudakhandi": (16, 0, 5, 0.20, 2),
    "purushottampur": (16, 1, 5, 0.22, 3),
    "patrapur": (12, 0, 5, 0.12, 2),
    "chikiti": (12, 0, 5, 0.12, 2),
    "hinjilicut": (13, 1, 5, 0.12, 3),
    "kabisuryanagar": (12, 1, 5, 0.10, 3),
    "polasara": (12, 1, 5, 0.10, 3),
    "beguniapada": (14, 1, 5, 0.12, 3),
    "digapahandi": (11, 1, 5, 0.08, 3),
    "aska": (10, 2, 5, 0.06, 4),
    "sanakhemundi": (8, 2, 5, 0.04, 4),
    "buguda": (9, 2, 5, 0.05, 4),
    "sorada": (8, 2, 5, 0.04, 4),
    "sheragada": (9, 2, 5, 0.04, 4),
    "dharakote": (7, 3, 5, 0.03, 5),
    "bhanjanagar": (7, 3, 5, 0.03, 5),
    "bellaguntha": (8, 3, 5, 0.03, 5),
    "jagannathprasad": (7, 3, 5, 0.02, 5),
}
PHAILIN_GAUGE_PEAKS = {"Rushikulya": 16.40, "Bahuda": 8.10, "Ghodahada": 11.20, "Badanadi": 13.10}
PHAILIN_TRACK = [
    (-24, 17.40, 86.60, 200),
    (-12, 18.30, 85.70, 215),
    (0, 19.25, 84.85, 215),
    (6, 19.80, 84.50, 150),
    (12, 20.30, 84.10, 100),
    (24, 21.20, 83.40, 60),
]
PHAILIN_REPORTS = [
    (
        -3,
        "Sea water entered Humma village, tidal surge, roofs flying, 15 families on school roof need boat",
        "whatsapp",
        "ganjam",
    ),
    (-2, "Gopalpur coast huts flattened, sea water inside houses, 25 people trapped", "sms", "rangeilunda"),
    (-2, "ଗଞ୍ଜାମ ସମୁଦ୍ର ପାଣି ଗାଁ ଭିତରେ, ଘର ଭାଙ୍ଗିଲା", "whatsapp", "ganjam"),
    (-1, "Chatrapur trees fell on road, electric pole down, roof collapsed, 3 injured", "app", "chhatrapur"),
    (-1, "Rushikulya mouth surge, water chest deep, 10 families stuck, rescue needed", "whatsapp", "ganjam"),
    (0, "Khalikote huts collapsed, people in open, need shelter and food", "sms", "khallikote"),
    (
        0,
        "Berhampur toofan, ped gir gaye, ghar toot gaya, 6 log ghayal, doctor chahiye",
        "whatsapp",
        "kukudakhandi",
    ),
    (1, "Ganjam block water waist deep, 50 people on roof, need boat urgently", "app", "ganjam"),
    (
        3,
        "Purushottampur low roads under water knee deep, families moving to shelter",
        "app",
        "purushottampur",
    ),
]
PHAILIN_TRUTH = {
    "ganjam": 0,
    "chhatrapur": 0,
    "rangeilunda": 0,
    "khallikote": 1,
    "kukudakhandi": 1,
    "purushottampur": 3,
    "patrapur": 2,
    "chikiti": 2,
    "hinjilicut": 3,
    "kabisuryanagar": 3,
    "polasara": 3,
    "beguniapada": 2,
    "digapahandi": 3,
}

NORMAL = {b: (1.2, 4, 6, 0.0, 99) for b in TITLI}
NORMAL_REPORTS = [
    (-5, "Small drain overflow near Berhampur bus stand, ankle deep water", "app", "kukudakhandi")
]


def rain_series(p: float, tp: float, sig: float, bg: float = 0.15) -> dict[int, float]:
    return {t: p * math.exp(-0.5 * ((t - tp) / sig) ** 2) + bg for t in range(-24 - SPIN, 25)}


def flood_series(fmax: float, tf: float) -> dict[int, float]:
    return {t: fmax / (1 + math.exp(-(t - tf) / 3.0)) for t in HOURS}


def gauge_series(
    rain_catch: dict[int, float], base: float, start: float, k: float, hi: float
) -> dict[int, float]:
    level = start
    out: dict[int, float] = {}
    for t in range(-24 - SPIN, 25):
        level = min(hi, base + (level - base) * RECESSION + k * rain_catch.get(t - 6, 0.0))
        if t >= -24:
            out[t] = level
    return out


def build(key, name, landfall, params, track, reports, gauge_peaks, geo, scale=None, gk=None, tf_shift=None):
    scale = scale or {}
    tf_shift = tf_shift or {}
    gk = gk or {}
    rains = {b: rain_series(p * scale.get(b, 1.0), tp, s) for b, (p, tp, s, _f, _tf) in params.items()}
    areas = {}
    for b, (_p, _tp, _s, fmax, tf) in params.items():
        r = rains[b]
        fl = flood_series(fmax, tf + tf_shift.get(b, 0.0))
        areas[b] = [
            {
                "t": t,
                "rain_1h_mm": round(r[t], 2),
                "rain_24h_mm": round(sum(r[x] for x in range(t - 23, t + 1)), 1),
                "flood_fraction": round(fl[t], 3),
            }
            for t in HOURS
        ]
    gauges = {}
    for g in geo.gauges.values():
        catch = [b.id for b in geo.catchment(g.id)]
        rc = {t: sum(rains[b][t] for b in catch) / len(catch) for t in range(-24 - SPIN, 25)}
        k = gk.get(g.river, 0.02)
        start = g.base_level_m + 0.2
        series = gauge_series(rc, g.base_level_m, start, k, g.max_level_m)
        gauges[g.river] = [{"t": t, "level_m": round(series[t], 2)} for t in HOURS]
    data = {
        "key": key,
        "name": name,
        "landfall_at": landfall,
        "note": "Illustrative reconstruction for demo — not observed data. Generated by scripts/gen_scenarios.py.",
        "hours": HOURS,
        "cyclone": {
            "name": track[0],
            "track": [{"t": t, "lat": la, "lon": lo, "vmax_kmh": v} for t, la, lo, v in track[1]],
        }
        if track
        else None,
        "gauges": gauges,
        "areas": areas,
        "reports": [{"t": t, "text": tx, "channel": ch, "area": a} for t, tx, ch, a in reports],
    }
    if not track:
        data.pop("cyclone")
    return data


def tune_gauges(key, name, landfall, params, track, reports, peaks, geo, scale, tf_shift=None):
    """Bisection on each gauge's response constant so its peak level hits `peaks`."""
    gk = {}
    for river, target in peaks.items():
        lo, hi = 0.0, 0.5
        for _ in range(40):
            mid = (lo + hi) / 2
            d = build(
                key, name, landfall, params, track, reports, peaks, geo, scale, {**gk, river: mid}, tf_shift
            )
            peak = max(p["level_m"] for p in d["gauges"][river])
            lo, hi = (mid, hi) if peak < target else (lo, mid)
        gk[river] = (lo + hi) / 2
    return gk


def score_at(data, geo, block, t=0):
    return ScenarioScorer(parse_scenario(data), geo).area(block, t).score


def _knob(x: float) -> tuple[float, float]:
    """One monotonic tuning knob -> (flood-onset shift h, rain scale).

    0..1 moves flood onset from 24 h late to 24 h early; 1..2 then raises rain up to 2x.
    """
    if x <= 1:
        return 24 - 48 * x, 1.0
    return -24.0, 1.0 + (x - 1)


def tune_titli(geo):
    shift: dict[str, float] = {}
    scale: dict[str, float] = {}
    gk: dict[str, float] = {}
    args = (
        "titli",
        "Replay: Cyclone Titli, Oct 2018",
        "2018-10-11T05:00:00+05:30",
        TITLI,
        ("Titli", TITLI_TRACK),
        TITLI_REPORTS,
    )
    for _round in range(4):
        gk = tune_gauges(*args, TITLI_GAUGE_PEAKS, geo, scale, shift)
        for block, target in TITLI_TARGETS.items():

            def score_with(x: float, block: str = block, gk: dict = gk) -> int:
                sh, sc = _knob(x)
                d = build(*args, TITLI_GAUGE_PEAKS, geo, {**scale, block: sc}, gk, {**shift, block: sh})
                return score_at(d, geo, block)

            def first_reaching(goal: int, score_with=score_with) -> float:
                lo, hi = 0.0, 2.0
                for _ in range(30):
                    mid = (lo + hi) / 2
                    lo, hi = (lo, mid) if score_with(mid) >= goal else (mid, hi)
                return hi

            # middle of the knob band that rounds to exactly `target`
            x = (first_reaching(target) + first_reaching(target + 1)) / 2
            shift[block], scale[block] = _knob(x)
    data = build(*args, TITLI_GAUGE_PEAKS, geo, scale, gk, shift)
    for block, target in TITLI_TARGETS.items():
        got = score_at(data, geo, block)
        if abs(got - target) > 1:
            print(f"WARNING: {block} scores {got} at t=0, target {target}")
    print(
        "tuning (flood shift h, rain scale):",
        {b: (round(shift[b], 2), round(scale[b], 2)) for b in TITLI_TARGETS},
    )
    return data, gk


def main() -> None:
    geo = load_geography(SEED)
    out = SEED / "scenarios"
    out.mkdir(parents=True, exist_ok=True)

    titli, gk_t = tune_titli(geo)
    phailin_args = (
        "phailin",
        "Replay: Cyclone Phailin, Oct 2013",
        "2013-10-12T21:00:00+05:30",
        PHAILIN,
        ("Phailin", PHAILIN_TRACK),
        PHAILIN_REPORTS,
    )
    gk_p = tune_gauges(*phailin_args, PHAILIN_GAUGE_PEAKS, geo, {})
    phailin = build(*phailin_args, PHAILIN_GAUGE_PEAKS, geo, {}, gk_p)
    normal = build(
        "normal",
        "Routine monsoon day (no cyclone)",
        "2024-07-15T12:00:00+05:30",
        NORMAL,
        None,
        NORMAL_REPORTS,
        {},
        geo,
        {},
        {r: 0.02 for r in TITLI_GAUGE_PEAKS},
    )

    for data in (titli, phailin, normal):
        (out / f"{data['key']}.json").write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
        )

    for key, truth in (("titli", TITLI_TRUTH), ("phailin", PHAILIN_TRUTH), ("normal", {})):
        (out / f"{key}.ground_truth.json").write_text(
            json.dumps(
                {
                    "key": key,
                    "note": "Illustrative list of blocks reported affected, with the hour (relative to landfall) "
                    "flooding/damage was observed. Compiled for demo; verify against OSDMA damage records.",
                    "affected": [{"area": a, "impact_t": t} for a, t in truth.items()],
                },
                indent=2,
            )
            + "\n"
        )

    # Fit nowcast k per gauge on both cyclone replays (least squares, 6 h horizon).
    gpath = SEED / "gauges.json"
    gj = json.loads(gpath.read_text())
    for g in gj["gauges"]:
        catch = [b.id for b in geo.catchment(g["id"])]
        num_lv, num_rn = [], []
        for data in (titli, phailin):
            num_lv.append([p["level_m"] for p in data["gauges"][g["river"]]])
            num_rn.append(
                [
                    sum(data["areas"][b][i]["rain_1h_mm"] for b in catch) / len(catch)
                    for i in range(len(HOURS))
                ]
            )
        ks = [fit_k(lv, rn) for lv, rn in zip(num_lv, num_rn, strict=True)]
        g["nowcast_k"] = round(sum(ks) / len(ks), 5)
    gpath.write_text(json.dumps(gj, indent=2) + "\n")

    geo = load_geography(SEED)
    print("Titli t=0:", {b: score_at(titli, geo, b) for b in TITLI_TARGETS})
    print("Phailin t=0 ganjam:", score_at(phailin, geo, "ganjam"))
    print("gauge k (titli):", {k: round(v, 4) for k, v in gk_t.items()})


if __name__ == "__main__":
    main()
