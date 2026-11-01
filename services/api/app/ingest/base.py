"""Pluggable ingestion adapters (PRD §6.3).

Each source has `live`, `file` and `scenario` implementations of
`fetch(window) -> list[Observation]`; which one runs is chosen per source in the
`data_source` table (Admin > Data sources).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class Observation:
    source: str  # weather | gauges | satellite | sachet
    key: str  # area code or gauge code
    valid_at: datetime
    values: dict[str, float]
    is_forecast: bool = False


class Adapter(ABC):
    source: str
    kind: str  # live | file | scenario | manual

    @abstractmethod
    def fetch(self, window: Window) -> list[Observation]: ...


REGISTRY: dict[tuple[str, str], type[Adapter]] = {}


def register(cls: type[Adapter]) -> type[Adapter]:
    REGISTRY[(cls.source, cls.kind)] = cls
    return cls
