"""Process-wide singletons for the demo sim clock."""

from app.risk.service import risk_service
from app.sim.clock import SimClock
from app.ws.hub import hub

sim_clock = SimClock(risk_service, hub)
