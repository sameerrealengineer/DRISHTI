"""Back-test CLI (PRD §11.6).

    cd services/api && uv run python ../../ml/backtest/run.py --scenario titli
    # or: make backtest

Writes reports/backtest_<scenario>.md and .json at the repo root.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.geo.static import load_geography  # noqa: E402
from app.risk.backtest import run_backtest, write_report  # noqa: E402
from app.sim.scenario import list_scenarios, load_scenario  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", default="all", help="scenario key, or 'all'")
    ap.add_argument("--seed", type=Path, default=ROOT / "seed")
    ap.add_argument("--out", type=Path, default=ROOT / "reports")
    args = ap.parse_args()

    geo = load_geography(args.seed)
    available = list_scenarios(args.seed)
    keys = [k for k in available if k != "normal"] if args.scenario == "all" else [args.scenario]
    for key in keys:
        truth_path = args.seed / "scenarios" / f"{key}.ground_truth.json"
        truth = json.loads(truth_path.read_text())
        res = run_backtest(load_scenario(available[key]), geo, truth)
        md, _ = write_report(res, args.out)
        print(
            f"{key}: recall={res['recall']} false_alarm_rate={res['false_alarm_rate']} "
            f"median_lead_h={res['median_lead_h']} -> {md.relative_to(ROOT)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
