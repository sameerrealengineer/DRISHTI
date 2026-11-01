# DRISHTI Ganjam (ଦୃଷ୍ଟି)

**AI-based hyperlocal disaster intelligence for Ganjam district, Odisha.**
OSFIC 2026 · Problem Statement PS-074 · Disaster Management · TeamGanjam, SMIT Berhampur
(lead developer Sameer Swain; mentor Er. Kiran Kumar Sethi).

DRISHTI fuses rainfall, river gauges, satellite flood maps and citizen reports into an hourly 0–100 risk
score for each of Ganjam's 22 blocks, forecasts which blocks will turn Severe in the next 12 hours, and
closes the loop from alert → SOS → rescue team → "rescued". Humans approve every alert.

> **Demo data.** All scenario, block and shelter data in this repository are approximate or illustrative
> reconstructions for demonstration. They are not official figures.

## Status

Milestones M0–M2 of the build plan (`PRD.md` §17) are done: repo and infrastructure, the full data model
with seed data, and the risk engine with forecast, scenario replay and back-test. See `CLAUDE.md` for
detail and what comes next.

| Check | Result |
|---|---|
| Titli replay at landfall | Purushottampur 83 · Patrapur 82 · Chikiti 72 · Sanakhemundi 70 · Aska 64 |
| Phailin replay at landfall | Ganjam 97 |
| Titli back-test | recall 85% · false alarms 0% · median lead 6 h (`reports/backtest_titli.md`) |
| Phailin back-test | recall 46% · lead −1 h — v1 forecast misses surge (`reports/backtest_phailin.md`) |

## Run it

With Docker:

```bash
cp .env.example .env
make up            # web http://localhost:8080 · API docs http://localhost:8000/api/v1/docs
```

Without Docker (needs PostgreSQL 16 + PostGIS 3.4, Redis, Python 3.11 with `uv`, Node 22):

```bash
cd services/api && uv sync && cd ../..
make migrate seed  # DATABASE_URL defaults to postgresql+psycopg://drishti:drishti@localhost:5432/drishti
make api           # terminal 1
cd apps/web && npm ci && npm run dev   # terminal 2 → http://localhost:5173/#/cc
```

Open the Command Centre, press ▶ and pick 16× to replay Cyclone Titli hour by hour.

## How the risk score works

`services/api/app/risk/engine.py` implements PRD §6.4 exactly:

```
Hazard   = 0.30·rain + 0.25·river + 0.25·satellite + 0.20·wind + 0.25·top1·top2
Exposure = 0.6·low-elevation + 0.4·near-coast
Vuln.    = 0.6·kutcha-houses + 0.4·population
Risk     = 100 · (Hazard·(0.55 + 0.45·Exposure)·(0.8 + 0.2·Vuln.) + 0.18·Citizen reports)
```

Every score carries its top drivers ("Rain 198 mm", "Rushikulya 106% of danger") and per-source
contribution bars. The 12-hour forecast uses forecast rain, a river nowcast, the cyclone track forecast
and persistence of satellite flooding.

## Repository

```
services/api     FastAPI app, Celery worker, Alembic migrations, tests
apps/web         Command Centre (React + TypeScript + Vite)
apps/citizen     Citizen Android app (Flutter) — M9
apps/field       Field Responder Android app (Flutter) — M10
packages/        design tokens; shared Dart package and OpenAPI client later
ml/              back-test harness; model training (M13)
seed/            blocks, gauges, shelters (sample), teams, demo users, scenarios
scripts/         seed/scenario generators
docs/            architecture, runbook, open questions
```

## API

OpenAPI: `/api/v1/openapi.json` (Swagger UI at `/api/v1/docs`). Implemented so far: `/healthz`,
`/readyz`, `/areas`, `/areas/geojson`, `/areas/locate`, `/gauges`, `/cyclone`, `/data-health`,
`/risk/latest|explain|history|district-curve|recompute|config`, `/sim/state|scenarios|play|pause|seek|
speed|scenario|reset`, and WebSocket `/ws` (`sim.tick`, `risk.updated`).

## Team

TeamGanjam — Sameer Swain (B.Tech CSE, SMIT Berhampur). Mentor: Er. Kiran Kumar Sethi.
Built with Claude Code.
