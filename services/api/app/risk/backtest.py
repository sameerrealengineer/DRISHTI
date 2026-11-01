"""Back-test harness (PRD §11.6): replay a scenario through the engine and compare
with the blocks reported affected (seed/scenarios/<key>.ground_truth.json).

Metrics are computed at two thresholds:
  High   (>=55) – an alert is auto-drafted (BE-AL-1); used for "recall of affected blocks"
  Severe (>=75) – used for "false alarm rate of Severe alerts" and "lead time of Severe warning"

For a threshold X:
  predicted   block reaches X at any replay hour
  warned at   first hour the block is >= X now, or forecast to reach X within 12 h
  lead time   impact_t (observed) - warned at, for correctly predicted blocks
  recall      |predicted ∩ truth| / |truth|;  false alarm rate  |predicted - truth| / |predicted|
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any

from app.geo.static import Geography
from app.risk.engine import DEFAULT_CONFIG
from app.risk.pipeline import AreaRisk, ScenarioScorer
from app.sim.scenario import Scenario


def _metrics(series: dict[str, list[AreaRisk]], impact: dict[str, float], thr: int) -> dict[str, Any]:
    pred, warned = set(), {}
    for bid, ss in series.items():
        if max(a.score for a in ss) >= thr:
            pred.add(bid)
            warned[bid] = next(a.t for a in ss if a.score >= thr or a.forecast_max_12h >= thr)
    actual = set(impact)
    tp = pred & actual
    leads = {b: impact[b] - warned[b] for b in tp}
    return {
        "threshold": thr,
        "predicted_count": len(pred),
        "true_positives": sorted(tp),
        "missed": sorted(actual - pred),
        "false_alarms": sorted(pred - actual),
        "recall": round(len(tp) / len(actual), 3) if actual else None,
        "false_alarm_rate": round(len(pred - actual) / len(pred), 3) if pred else 0.0,
        "median_lead_h": median(leads.values()) if leads else None,
        "warned_at": warned,
        "lead_h": leads,
    }


def run_backtest(
    scn: Scenario, geo: Geography, truth: dict[str, Any], config: dict | None = None
) -> dict[str, Any]:
    cfg = config or DEFAULT_CONFIG
    th = cfg["thresholds"]
    scorer = ScenarioScorer(scn, geo, cfg)
    hours = list(range(scn.t_min, scn.t_max + 1))
    impact = {a["area"]: a["impact_t"] for a in truth.get("affected", [])}
    series = {bid: [scorer.area(bid, t) for t in hours] for bid in geo.blocks}

    high = _metrics(series, impact, th["high"])
    severe = _metrics(series, impact, th["severe"])

    blocks = []
    for bid, ss in series.items():
        peak = max(ss, key=lambda a: a.score)
        blocks.append(
            {
                "area": bid,
                "name": geo.blocks[bid].name,
                "peak_score": peak.score,
                "peak_level": peak.level,
                "peak_t": peak.t,
                "affected": bid in impact,
                "impact_t": impact.get(bid),
                "high_warned_t": high["warned_at"].get(bid),
                "severe_warned_t": severe["warned_at"].get(bid),
                "high_lead_h": high["lead_h"].get(bid),
                "severe_lead_h": severe["lead_h"].get(bid),
            }
        )

    return {
        "scenario": scn.key,
        "name": scn.name,
        "config_version": cfg.get("version", 1),
        "truth_count": len(impact),
        # Headline metrics, as defined in PRD §2.3
        "recall": high["recall"],
        "false_alarm_rate": severe["false_alarm_rate"],
        "median_lead_h": severe["median_lead_h"],
        "high": {k: v for k, v in high.items() if k not in ("warned_at", "lead_h")},
        "severe": {k: v for k, v in severe.items() if k not in ("warned_at", "lead_h")},
        "targets": {"recall": 0.80, "false_alarm_rate": 0.25, "lead_h": 6},
        "blocks": sorted(blocks, key=lambda b: -b["peak_score"]),
        "note": "Scenario data are illustrative reconstructions; these numbers test the pipeline, "
        "not real-world skill.",
    }


def to_markdown(res: dict[str, Any]) -> str:
    def pct(x):
        return "n/a" if x is None else f"{100 * x:.0f}%"

    def fmt(v):
        return "—" if v is None else (f"{v:+g}" if isinstance(v, int | float) else str(v))

    hi, sv = res["high"], res["severe"]
    lines = [
        f"# Back-test: {res['name']}",
        "",
        f"> {res['note']}",
        "",
        f"Risk config v{res['config_version']} · {res['truth_count']} blocks reported affected",
        "",
        "| Metric (PRD §2.3) | Result | Target |",
        "|---|---|---|",
        f"| Recall of affected blocks (alerted, High+) | {pct(hi['recall'])} "
        f"({len(hi['true_positives'])}/{res['truth_count']}) | ≥ 80% |",
        f"| False alarm rate of Severe alerts | {pct(sv['false_alarm_rate'])} "
        f"({len(sv['false_alarms'])}/{sv['predicted_count']}) | ≤ 25% |",
        f"| Median lead time of Severe warning | {fmt(sv['median_lead_h'])} h | ≥ 6 h |",
        "",
        "| Threshold | Recall | False alarm rate | Median lead h | Missed | False alarms |",
        "|---|---|---|---|---|---|",
    ]
    for name, m in (("High (≥55)", hi), ("Severe (≥75)", sv)):
        lines.append(
            f"| {name} | {pct(m['recall'])} | {pct(m['false_alarm_rate'])} | {fmt(m['median_lead_h'])} | "
            f"{', '.join(m['missed']) or '—'} | {', '.join(m['false_alarms']) or '—'} |"
        )
    lines += [
        "",
        "Times are hours relative to landfall.",
        "",
        "| Block | Peak | Level | Peak t | Affected | Impact t | High warned | Severe warned "
        "| Severe lead h |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for b in res["blocks"]:
        lines.append(
            f"| {b['name']} | {b['peak_score']} | {b['peak_level']} | {fmt(b['peak_t'])} | "
            f"{'yes' if b['affected'] else 'no'} | {fmt(b['impact_t'])} | {fmt(b['high_warned_t'])} | "
            f"{fmt(b['severe_warned_t'])} | {fmt(b['severe_lead_h'])} |"
        )
    return "\n".join(lines) + "\n"


def write_report(res: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"backtest_{res['scenario']}.md"
    js = out_dir / f"backtest_{res['scenario']}.json"
    md.write_text(to_markdown(res))
    js.write_text(json.dumps(res, indent=2) + "\n")
    return md, js
