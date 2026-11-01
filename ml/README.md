# ML

PRD §11. Each model gets `README.md`, `train.py`, `evaluate.py`, `predict.py`, `MODEL_CARD.md` (M13).

- `backtest/run.py` — replay scenarios through the engine and score against ground truth (§11.6).
- v1 rule-based models live in the API: `services/api/app/forecast/nowcast.py`,
  `services/api/app/reports/triage.py`.
