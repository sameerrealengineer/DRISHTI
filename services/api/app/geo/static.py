"""Static geography loaded from seed files (pure; no DB).

The API builds the same objects from database rows; the back-test harness and
unit tests use the seed files directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Block:
    id: str
    name: str
    name_or: str
    lat: float
    lon: float
    elevation_m: float
    coast_km: float
    river: str | None
    gauge: str | None
    population: int
    kutcha_share: float


@dataclass(frozen=True)
class GaugeDef:
    id: str
    name: str
    river: str
    site: str
    area: str
    lat: float
    lon: float
    danger_level_m: float
    warning_level_m: float
    base_level_m: float
    max_level_m: float
    nowcast_k: float = 0.004


@dataclass
class Geography:
    blocks: dict[str, Block]
    gauges: dict[str, GaugeDef]
    aliases: dict[str, str] = field(default_factory=dict)

    def gauge_for_river(self, river: str) -> GaugeDef | None:
        return next((g for g in self.gauges.values() if g.river == river), None)

    def catchment(self, gauge_id: str) -> list[Block]:
        return [b for b in self.blocks.values() if b.gauge == gauge_id]

    @property
    def place_names(self) -> dict[str, str]:
        """lower-case English + Odia block names -> block id (for report triage)."""
        names: dict[str, str] = {}
        for b in self.blocks.values():
            names[b.name.lower()] = b.id
            if b.name_or:
                names[b.name_or] = b.id
        return names


def load_geography(seed_dir: Path) -> Geography:
    bj = json.loads((seed_dir / "blocks.json").read_text())
    gj = json.loads((seed_dir / "gauges.json").read_text())
    aj = json.loads((seed_dir / "aliases.json").read_text()) if (seed_dir / "aliases.json").exists() else {}
    blocks = {
        b["id"]: Block(
            id=b["id"],
            name=b["name"],
            name_or=b.get("name_or") or "",
            lat=b["lat"],
            lon=b["lon"],
            elevation_m=b["elevation_m"],
            coast_km=b["coast_km"],
            river=b.get("river"),
            gauge=b.get("gauge"),
            population=b["population"],
            kutcha_share=b["kutcha_share"],
        )
        for b in bj["blocks"]
    }
    fields = GaugeDef.__dataclass_fields__
    gauges = {g["id"]: GaugeDef(**{k: v for k, v in g.items() if k in fields}) for g in gj["gauges"]}
    return Geography(blocks=blocks, gauges=gauges, aliases=aj.get("aliases", {}))


@lru_cache
def default_geography() -> Geography:
    from app.config import get_settings

    return load_geography(get_settings().seed_dir)
