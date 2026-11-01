"""Demo sim controls (PRD §15.8, DEMO-3). DEMO mode only; RBAC (DISTRICT+) is added in M3."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.config import get_settings
from app.db import get_db
from app.seed.loader import reset_runtime
from app.sim.scenario import list_scenarios
from app.sim.state import sim_clock

router = APIRouter(prefix="/sim", tags=["sim"])


def demo_only() -> None:
    if not get_settings().is_demo:
        raise ApiError(403, "demo_only", "sim controls are available in DEMO mode only")


class SeekIn(BaseModel):
    t_hours: float


class SpeedIn(BaseModel):
    speed: float


class ScenarioIn(BaseModel):
    key: str


@router.get("/state")
def state():
    return sim_clock.state()


@router.get("/scenarios")
def scenarios():
    from app.sim.scenario import load_scenario

    return {"items": [load_scenario(p).summary() for p in list_scenarios(get_settings().seed_dir).values()]}


@router.post("/play", dependencies=[Depends(demo_only)])
async def play():
    return await sim_clock.play()


@router.post("/pause", dependencies=[Depends(demo_only)])
async def pause():
    return await sim_clock.pause()


@router.post("/seek", dependencies=[Depends(demo_only)])
async def seek(body: SeekIn):
    return await sim_clock.seek(body.t_hours)


@router.post("/speed", dependencies=[Depends(demo_only)])
async def speed(body: SpeedIn):
    try:
        return await sim_clock.set_speed(body.speed)
    except ValueError as exc:
        raise ApiError(422, "validation_error", str(exc)) from exc


@router.post("/scenario", dependencies=[Depends(demo_only)])
async def scenario(body: ScenarioIn):
    try:
        return await sim_clock.set_scenario(body.key)
    except KeyError as exc:
        raise ApiError(404, "not_found", f"scenario {body.key} not found") from exc


@router.post("/reset", dependencies=[Depends(demo_only)])
async def reset(db: Session = Depends(get_db)):
    """DEMO-6: clear runtime tables, reload the scenario, rewind the clock."""
    reset_runtime(db)
    return await sim_clock.set_scenario(sim_clock.scenario_key)
