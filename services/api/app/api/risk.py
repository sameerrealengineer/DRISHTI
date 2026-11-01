"""Risk and forecast (PRD §15.3). RBAC is added in M3."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db import get_db
from app.risk.service import risk_service
from app.sim.state import sim_clock

router = APIRouter(prefix="/risk", tags=["risk"])


def _need_scenario() -> None:
    if risk_service.scenario is None:
        raise ApiError(503, "not_ready", "risk engine has no data loaded yet")


@router.get("/latest")
def latest():
    _need_scenario()
    return risk_service.latest(sim_clock.t)


@router.get("/explain/{code}")
def explain(code: str):
    _need_scenario()
    if code not in risk_service.geo.blocks:
        raise ApiError(404, "not_found", f"area {code} not found")
    ar = risk_service.hour(sim_clock.t)[code]
    v = risk_service.area_view(ar)
    r = ar.result
    v["text"] = (
        f"{v['name']} scores {r.score} ({r.level}). Hazard {r.hazard:.2f} from "
        f"{', '.join(r.drivers) or 'no strong drivers'}; exposure {r.exposure:.2f}; "
        f"vulnerability {r.vulnerability:.2f}; citizen signal {r.citizen:.2f}."
    )
    return v


@router.get("/history")
def history(area: str):
    _need_scenario()
    if area not in risk_service.geo.blocks:
        raise ApiError(404, "not_found", f"area {area} not found")
    return {"area": area, "scenario": risk_service.scenario.key, "points": risk_service.area_history(area)}


@router.get("/district-curve")
def district_curve():
    _need_scenario()
    return risk_service.district_curve()


@router.post("/recompute")
def recompute(db: Session = Depends(get_db)):
    _need_scenario()
    risk_service.load(db, risk_service.scenario.key)
    return {"ok": True, "config_version": risk_service.config.get("version", 1)}


@router.get("/config")
def get_config():
    return risk_service.config
