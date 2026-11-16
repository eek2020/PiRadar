from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from piradar.aircraft_icons import icon_family


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
    registration: str = ""
    aircraft_type: str = ""
    category: str = ""
    squawk: str = ""
    military: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["icon"] = icon_family(self.aircraft_type, self.category)
        return payload
