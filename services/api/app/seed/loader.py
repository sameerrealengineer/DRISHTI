"""Seed loader (PRD M1): loads seed/*.json into the database.

uv run python -m app.seed.loader            # load if empty
uv run python -m app.seed.loader --reset    # wipe everything and reload
uv run python -m app.seed.loader --runtime  # demo reset: clear runtime tables only (DEMO-6)
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, Point, shape
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import models as m
from app.config import get_settings
from app.db import session_factory
from app.risk.engine import DEFAULT_CONFIG
from app.security.crypto import encrypt_phone, hash_secret, phone_hash
from app.seed.voronoi import voronoi_cells
from app.sim.scenario import list_scenarios, load_scenario

# Cleared by a demo reset; everything else is reference data.
RUNTIME_TABLES = [
    "task_event",
    "task",
    "report_media",
    "report",
    "shelter_need",
    "shelter_occupancy",
    "dispatch",
    "allocation",
    "alert",
    "safety_status",
    "outbox",
    "risk_score",
    "gauge_reading",
    "weather_obs",
    "satellite_obs",
    "cyclone_track_point",
    "cyclone",
    "external_alert",
]
ALL_TABLES = RUNTIME_TABLES + [
    "citizen_profile",
    "app_user",
    "team",
    "shelter",
    "gauge",
    "area_alias",
    "area",
    "resource_pool",
    "district",
    "risk_config",
    "sim_state",
    "scenario",
    "feature_flag",
    "data_source",
]

RESOURCE_DEFAULTS = {"teams": 24, "boats": 60, "med": 18, "kits": 20000}  # §21.7
FEATURE_FLAGS = {
    "RISK_MODEL": "rules",
    "REPORT_AI": "rules",
    "IMAGE_AI": "heuristic",
    "SAT_SOURCE": "scenario",
    "GAUGE_SOURCE": "scenario",
    "SMS_PROVIDER": "simulated",
    "WHATSAPP_PROVIDER": "simulated",
    "VOICE_PROVIDER": "simulated",
    "AUTO_ASSIGN": "on",
    "STANDALONE_WEB": "off",
}
DATA_SOURCES = {"weather": "scenario", "gauges": "scenario", "satellite": "scenario", "sachet": "file"}


def _read(seed: Path, name: str) -> dict:
    return json.loads((seed / name).read_text())


def _pt(lon: float, lat: float):
    return from_shape(Point(lon, lat), srid=4326)


def truncate(db: Session, tables: list[str]) -> None:
    # audit_log is append-only (trigger); TRUNCATE bypasses row triggers, which is what a full reset wants.
    db.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))


def load_all(db: Session, seed: Path | None = None) -> dict[str, int]:
    seed = seed or get_settings().seed_dir
    now = datetime.now(UTC)

    # district
    outline_fc = _read(seed, "district_outline.geojson")
    outline = shape(outline_fc["features"][0]["geometry"])
    bj = _read(seed, "blocks.json")
    dist = m.District(
        name=bj["district"]["name"],
        code=bj["district"]["code"],
        geom=from_shape(MultiPolygon([outline]), srid=4326),
    )
    db.add(dist)
    db.flush()

    # blocks with Voronoi polygons
    cells = voronoi_cells({b["id"]: (b["lon"], b["lat"]) for b in bj["blocks"]}, outline)
    areas: dict[str, m.Area] = {}
    for b in bj["blocks"]:
        a = m.Area(
            district_id=dist.id,
            kind="block",
            name=b["name"],
            name_or=b.get("name_or"),
            code=b["id"],
            centroid=_pt(b["lon"], b["lat"]),
            geom=from_shape(cells[b["id"]], srid=4326),
            geometry_source="voronoi_approx",
            elevation_m=b["elevation_m"],
            coast_km=b["coast_km"],
            river=b.get("river"),
            population=b["population"],
            households=b.get("households"),
            kutcha_share=b["kutcha_share"],
            attrs_approx=True,
        )
        db.add(a)
        areas[b["id"]] = a
    db.flush()

    aliases = _read(seed, "aliases.json")["aliases"] if (seed / "aliases.json").exists() else {}
    for alias, bid in aliases.items():
        db.add(m.AreaAlias(area_id=areas[bid].id, alias=alias.lower()))

    # gauges
    for g in _read(seed, "gauges.json")["gauges"]:
        db.add(
            m.Gauge(
                code=g["id"],
                name=g["name"],
                river=g["river"],
                site=g["site"],
                area_id=areas[g["area"]].id,
                location=_pt(g["lon"], g["lat"]),
                danger_level_m=g["danger_level_m"],
                warning_level_m=g.get("warning_level_m"),
                danger_level_sourced=g.get("danger_level_sourced", False),
            )
        )

    # risk config v1
    db.add(
        m.RiskConfig(
            version=1,
            weights={k: DEFAULT_CONFIG[k] for k in ("weights", "norms", "report_weights")},
            thresholds=DEFAULT_CONFIG["thresholds"],
            active=True,
        )
    )

    # resource pools
    for kind, total in RESOURCE_DEFAULTS.items():
        db.add(m.ResourcePool(district_id=dist.id, kind=kind, total=total))

    # teams
    teams: dict[str, m.Team] = {}
    for t in _read(seed, "teams.json")["teams"]:
        team = m.Team(
            name=t["name"],
            type=t["type"],
            capabilities=t["capabilities"],
            members_count=t["members"],
            base_location=_pt(t["lon"], t["lat"]),
            current_location=_pt(t["lon"], t["lat"]),
            base_area_id=areas[t["base_block"]].id,
            status="available",
            code=t["code"],
            pin_hash=hash_secret(t["pin"]),
        )
        db.add(team)
        teams[t["code"]] = team
    db.flush()

    # shelters (sample)
    for s in _read(seed, "shelters.json")["shelters"]:
        db.add(
            m.Shelter(
                code=s["code"],
                name=s["name"],
                type=s["type"],
                area_id=areas[s["block"]].id,
                location=_pt(s["lon"], s["lat"]),
                capacity=s["capacity"],
                occupancy=0,
                facilities=s["facilities"],
                incharge_name=s["incharge_name"],
                incharge_phone_enc=encrypt_phone(s["incharge_phone"]),
                status=s["status"],
                is_sample=True,
            )
        )

    # users
    for u in _read(seed, "users.json")["users"]:
        user = m.AppUser(
            name=u["name"],
            role=u["role"],
            email=u.get("email"),
            password_hash=hash_secret(u["password"]) if u.get("password") else None,
            phone_hash=phone_hash(u["phone"]) if u.get("phone") else None,
            phone_enc=encrypt_phone(u["phone"]) if u.get("phone") else None,
            area_id=areas[u["block"]].id if u.get("block") else None,
            team_id=teams[u["team"]].id if u.get("team") else None,
            language=u.get("language", "or"),
        )
        db.add(user)
        db.flush()
        if u["role"] == "CITIZEN":
            db.add(
                m.CitizenProfile(
                    user_id=user.id,
                    area_id=user.area_id,
                    home_label=u.get("home_label"),
                    home_location=_pt(u["home_lon"], u["home_lat"]) if u.get("home_lat") else None,
                    consent_at=now,
                )
            )

    # scenarios + sim state
    for key, path in list_scenarios(seed).items():
        scn = load_scenario(path)
        db.add(
            m.Scenario(
                key=key,
                name=scn.name,
                landfall_at=scn.landfall_at,
                description=scn.note,
                data_uri=str(path.relative_to(seed.parent)),
            )
        )
    default = get_settings().sim_default_scenario
    scn = load_scenario(list_scenarios(seed)[default])
    db.add(m.SimState(scenario_key=default, sim_time=scn.sim_time(scn.t_min), playing=False, speed=1.0))

    for key, val in FEATURE_FLAGS.items():
        db.add(m.FeatureFlag(key=key, enabled=val not in ("off",), payload={"value": val}))
    for key, adapter in DATA_SOURCES.items():
        db.add(m.DataSource(key=key, adapter=adapter))

    db.commit()
    return counts(db)


def counts(db: Session) -> dict[str, int]:
    def n(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    return {
        "blocks": n(m.Area, m.Area.kind == "block"),
        "blocks_with_polygon": n(m.Area, m.Area.kind == "block", m.Area.geom.is_not(None)),
        "gauges": n(m.Gauge),
        "shelters": n(m.Shelter),
        "teams": n(m.Team),
        "users": n(m.AppUser),
        "scenarios": n(m.Scenario),
    }


def reset_runtime(db: Session) -> None:
    """DEMO-6: clear runtime tables and restore shelters/teams to their seeded state."""
    truncate(db, RUNTIME_TABLES)
    db.execute(text("UPDATE shelter SET occupancy = 0, status = 'ready'"))
    db.execute(
        text("UPDATE team SET status = 'available', current_location = base_location, last_ping_at = NULL")
    )
    db.commit()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="wipe all tables and reload seed")
    ap.add_argument("--runtime", action="store_true", help="clear runtime tables only (demo reset)")
    args = ap.parse_args()
    with session_factory()() as db:
        if args.runtime:
            reset_runtime(db)
            print("runtime tables cleared")
            return
        if args.reset:
            truncate(db, ALL_TABLES)
            db.commit()
        elif counts(db)["blocks"]:
            print("already seeded:", counts(db))
            return
        print("seeded:", load_all(db))


if __name__ == "__main__":
    main()
