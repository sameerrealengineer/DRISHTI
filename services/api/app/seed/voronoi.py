"""Approximate block polygons: Voronoi cells of block centroids clipped to the
district outline (BE-GEO-2). Computed in a local km grid so cells are not
stretched by lon/lat distortion. Marked geometry_source='voronoi_approx'.
"""

from __future__ import annotations

import math

from shapely import affinity
from shapely.geometry import MultiPoint, MultiPolygon, Point, Polygon
from shapely.ops import voronoi_diagram


def voronoi_cells(points: dict[str, tuple[float, float]], outline: Polygon) -> dict[str, MultiPolygon]:
    """points: id -> (lon, lat). Returns id -> MultiPolygon (lon/lat)."""
    lat0 = outline.centroid.y
    kx = math.cos(math.radians(lat0))

    def to_km(g):
        return affinity.scale(g, xfact=kx, yfact=1.0, origin=(0, 0))

    def to_deg(g):
        return affinity.scale(g, xfact=1 / kx, yfact=1.0, origin=(0, 0))

    outline_km = to_km(outline)
    pts_km = {k: to_km(Point(lon, lat)) for k, (lon, lat) in points.items()}
    cells = voronoi_diagram(MultiPoint(list(pts_km.values())), envelope=outline_km.buffer(1.0))

    out: dict[str, MultiPolygon] = {}
    for cell in cells.geoms:
        owner = next((k for k, p in pts_km.items() if cell.contains(p)), None)
        if owner is None:
            continue
        clipped = to_deg(cell.intersection(outline_km))
        if clipped.is_empty:
            continue
        if isinstance(clipped, Polygon):
            clipped = MultiPolygon([clipped])
        elif not isinstance(clipped, MultiPolygon):
            clipped = MultiPolygon([g for g in getattr(clipped, "geoms", []) if isinstance(g, Polygon)])
        out[owner] = clipped
    missing = set(points) - set(out)
    if missing:
        raise ValueError(f"no Voronoi cell for: {sorted(missing)} (centroid outside outline?)")
    return out
