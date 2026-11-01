"""Build schematic geography seed files for Ganjam (approximate, for demo).

Writes seed/district_outline.geojson, seed/coastline.geojson, seed/rivers.geojson
and fills `coast_km` in seed/blocks.json. Re-run after editing block centroids.

    python scripts/build_geo_seed.py
"""

import json
import math
from pathlib import Path

SEED = Path(__file__).resolve().parents[1] / "seed"

# Schematic district outline (lon, lat), clockwise from the south coast.
# The first 6 points are the Bay of Bengal coastline (Sonapur -> Chilika mouth).
COAST = [(84.80, 19.08), (84.91, 19.26), (85.05, 19.38), (85.12, 19.52), (85.20, 19.72)]
INLAND = [
    (85.05, 19.85),
    (84.85, 20.00),
    (84.60, 20.15),
    (84.35, 20.10),
    (84.25, 19.90),
    (84.30, 19.65),
    (84.28, 19.40),
    (84.35, 19.20),
    (84.45, 19.05),
    (84.60, 19.00),
]
OUTLINE = COAST + INLAND + [COAST[0]]

# Schematic river lines (lon, lat) from upstream to mouth.
RIVERS = {
    "Rushikulya": [
        (84.38, 19.98),
        (84.55, 19.88),
        (84.66, 19.70),
        (84.78, 19.58),
        (84.89, 19.52),
        (85.07, 19.40),
    ],
    "Badanadi": [(84.42, 19.72), (84.55, 19.65), (84.66, 19.60), (84.72, 19.58)],
    "Ghodahada": [(84.40, 19.50), (84.57, 19.37), (84.70, 19.30), (84.86, 19.24)],
    "Bahuda": [(84.45, 19.15), (84.58, 19.12), (84.70, 19.10), (84.80, 19.08)],
}

KM_LAT = 111.0
KM_LON = 111.0 * math.cos(math.radians(19.5))


def _xy(lon: float, lat: float) -> tuple[float, float]:
    return lon * KM_LON, lat * KM_LAT


def dist_point_segment_km(p, a, b) -> float:
    px, py = _xy(*p)
    ax, ay = _xy(*a)
    bx, by = _xy(*b)
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def coast_km(lon: float, lat: float) -> float:
    return min(dist_point_segment_km((lon, lat), COAST[i], COAST[i + 1]) for i in range(len(COAST) - 1))


def main() -> None:
    def fc(features):
        return {"type": "FeatureCollection", "features": features}

    (SEED / "district_outline.geojson").write_text(
        json.dumps(
            fc(
                [
                    {
                        "type": "Feature",
                        "properties": {"name": "Ganjam", "code": "GJM", "source": "schematic_approx"},
                        "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in OUTLINE]]},
                    }
                ]
            ),
            indent=1,
        )
    )
    (SEED / "coastline.geojson").write_text(
        json.dumps(
            fc(
                [
                    {
                        "type": "Feature",
                        "properties": {"name": "Bay of Bengal coast", "source": "schematic_approx"},
                        "geometry": {"type": "LineString", "coordinates": [list(p) for p in COAST]},
                    }
                ]
            ),
            indent=1,
        )
    )
    (SEED / "rivers.geojson").write_text(
        json.dumps(
            fc(
                [
                    {
                        "type": "Feature",
                        "properties": {"name": n, "source": "schematic_approx"},
                        "geometry": {"type": "LineString", "coordinates": [list(p) for p in pts]},
                    }
                    for n, pts in RIVERS.items()
                ]
            ),
            indent=1,
        )
    )

    blocks_path = SEED / "blocks.json"
    data = json.loads(blocks_path.read_text())
    for b in data["blocks"]:
        b["coast_km"] = round(coast_km(b["lon"], b["lat"]), 1)
    blocks_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote geo seed; coast_km for {len(data['blocks'])} blocks")


if __name__ == "__main__":
    main()
