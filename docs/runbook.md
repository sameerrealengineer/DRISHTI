# Runbook

## Start / stop

```bash
make up      # docker compose up --build -d
make down
make logs
```

The API container runs `alembic upgrade head`, then loads seed data if the DB is empty, then starts
uvicorn. Health: `GET /healthz` (process up), `GET /readyz` (DB + Redis reachable, 503 otherwise).

## Demo controls

- Reset the demo (clears reports, tasks, alerts, outbox, risk history; restores shelters and teams):
  `POST /api/v1/sim/reset` or `make demo`.
- Switch scenario: `POST /api/v1/sim/scenario {"key": "titli" | "phailin" | "normal"}`.
- Seek: `POST /api/v1/sim/seek {"t_hours": -6}`; speed: `POST /api/v1/sim/speed {"speed": 16}`.

## Data

- Re-seed everything: `make seed-reset` (wipes all tables).
- Regenerate scenarios after editing `seed/blocks.json` or `scripts/gen_scenarios.py`:
  `python scripts/build_geo_seed.py && make scenarios && make test`.

## Backups

Daily `pg_dump` to object storage and the restore procedure are to be added with deployment (PRD §16.2).
