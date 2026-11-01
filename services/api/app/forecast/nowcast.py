"""River level nowcast v1 — PRD §11.2.

    level(t+h) = level(t) + k_r * sum(rain_catchment(tau)),  tau in (t-6, t+h-6]

`rain_catchment` is the mean hourly rain (mm) over the blocks draining to the
gauge. The 6 h lag approximates travel time to the gauge. The result is clamped
to the gauge's physical bounds. k_r is fitted per river by least squares
(`fit_k`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

LAG_H = 6


def nowcast_level(
    level_now: float,
    rain_catchment: Callable[[int], float],
    t: int,
    h: int,
    k: float,
    bounds: tuple[float, float],
) -> float:
    total = sum(rain_catchment(tau) for tau in range(t - LAG_H + 1, t + h - LAG_H + 1))
    lo, hi = bounds
    return max(lo, min(hi, level_now + k * total))


def fit_k(levels: Sequence[float], rain: Sequence[float], h: int = 6) -> float:
    """Least-squares k for  level[t+h] - level[t] = k * sum(rain[t-5 .. t+h-6]).

    `levels` and `rain` are aligned hourly series. Returns 0 if there is no signal.
    """
    num = den = 0.0
    for t in range(LAG_H, len(levels) - h):
        x = sum(rain[t - LAG_H + 1 : t + h - LAG_H + 1])
        y = levels[t + h] - levels[t]
        num += x * y
        den += x * x
    return num / den if den > 0 else 0.0
