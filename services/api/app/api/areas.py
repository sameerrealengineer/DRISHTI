"""Geography, gauges, data health (PRD §15.2)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import ST_AsGeoJSON, ST_Contains, ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.api.errors import ApiError
from app.db import get_db
from app.risk.service import risk_service
from app.sim.state import sim_clock

router = APIRouter(tags=["geography"])

STATIC_FIELDS = ("elevation_m", "coast_km", "river", "population", "households", "kutcha_share")


def _area_dict(a: m.Area) -> dict[str, Any]:
    return {
        "id": a.id,
        "code": a.code,
        "kind": a.kind,
        "name": a.name,
        "name_or": a.name_or,
        "geometry_source": a.geometry_source,
        "attrs_approx": a.attrs_approx,
        **{f: getattr(a, f) for f in STATIC_FIELDS},
    }


def _latest_by_code() -> dict[str, dict[str, Any]]:
    if risk_service.scenario is None:
        return {}
    return {x["code"]: x for x in risk_service.latest(sim_clock.t)["areas"]}


@router.get("/areas")
def list_areas(kind: str = "block", db: Session = Depends(get_db)):
    rows = db.scalars(
        select(m.Area).where(m.Area.kind == kind, m.Area.is_active.is_(True)).order_by(m.Area.name)
    )
    return {"items": [_area_dict(a) for a in rows]}


@router.get("/areas/geojson")
def areas_geojson(kind: str = "block", db: Session = Depends(get_db)):
    latest = _latest_by_code()
    rows = db.execute(
        select(m.Area, ST_AsGeoJSON(m.Area.geom, 5), ST_AsGeoJSON(m.Area.centroid, 5)).where(
            m.Area.kind == kind
        )
    ).all()
    feats = []
    for a, geom, centroid in rows:
        r = latest.get(a.code, {})
        feats.append(
            {
                "type": "Feature",
                "id": a.id,
                "geometry": json.loads(geom) if geom else None,
                "properties": {
                    **_area_dict(a),
                    "centroid": json.loads(centroid)["coordinates"] if centroid else None,
                    "score": r.get("score"),
                    "level": r.get("level"),
                    "hours_to_severe": r.get("hours_to_severe"),
                },
            }
        )
    return {"type": "FeatureCollection", "features": feats}


@router.get("/areas/locate")
def locate(
    lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180), db: Session = Depends(get_db)
):
    """BE-GEO-5: point -> block (ST_Contains), falling back to the nearest centroid."""
    pt = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    area = db.scalar(select(m.Area).where(m.Area.kind == "block", ST_Contains(m.Area.geom, pt)))
    method = "contains"
    if area is None:
        area = db.scalar(
            select(m.Area).where(m.Area.kind == "block").order_by(ST_Distance(m.Area.centroid, pt))
        )
        method = "nearest_centroid"
    if area is None:
        raise ApiError(404, "not_found", "no areas loaded")
    return {"block": _area_dict(area), "gp": None, "village": None, "method": method}


@router.get("/areas/{code}")
def get_area(code: str, db: Session = Depends(get_db)):
    a = db.scalar(select(m.Area).where(m.Area.code == code))
    if a is None:
        raise ApiError(404, "not_found", f"area {code} not found")
    return {**_area_dict(a), "risk": _latest_by_code().get(code)}


@router.get("/gauges")
def gauges():
    return {"items": risk_service.gauges(sim_clock.t)}


@router.get("/gauges/{code}/readings")
def gauge_readings(code: str):
    if code not in risk_service.geo.gauges:
        raise ApiError(404, "not_found", f"gauge {code} not found")
    return {"gauge": code, "items": risk_service.gauge_readings(code, sim_clock.t), "source": "scenario"}


@router.get("/cyclone")
def cyclone():
    return risk_service.cyclone(sim_clock.t)


@router.get("/data-health")
def data_health(db: Session = Depends(get_db)):
    """BE-ING-7. In DEMO mode every source is the scenario adapter and is always fresh."""
    rows = db.scalars(select(m.DataSource).order_by(m.DataSource.key)).all()
    items = [
        {
            "key": r.key,
            "adapter": r.adapter,
            "last_success_at": r.last_success_at,
            "last_error": r.last_error,
            "status": "green" if r.adapter == "scenario" else "red" if r.last_success_at is None else "green",
        }
        for r in rows
    ]
    worst = (
        "red"
        if any(i["status"] == "red" for i in items)
        else "amber"
        if any(i["status"] == "amber" for i in items)
        else "green"
    )
    return {"status": worst, "items": items}
