# Worker

Celery worker and beat reuse the API code (`services/api/app/worker/celery_app.py`) and the same
Docker image, so there is no separate package here. See `docker-compose.yml` (`worker`, `beat`).

```bash
cd services/api
uv run celery -A app.worker.celery_app worker -l info
uv run celery -A app.worker.celery_app beat -l info
```
