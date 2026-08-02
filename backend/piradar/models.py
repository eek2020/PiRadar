from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Aircraft:
    hex: str
    callsign: str
    latitude: float
    longitude: float
    altitude_ft: int
    ground_speed_kt: int
    track_deg: int
    vertical_rate_fpm: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

