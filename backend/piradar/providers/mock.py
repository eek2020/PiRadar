from __future__ import annotations

import math
import time
from typing import Any

from piradar.aircraft_types import describe_aircraft_type, describe_operator
from piradar.models import Aircraft


class MockAircraftProvider:
    """Deterministic moving tracks for UI development and offline demos."""

    name = "mock"

    @property
    def status(self) -> str:
        return "live"

    def __init__(self, home_latitude: float, home_longitude: float) -> None:
        self.home_latitude = home_latitude
        self.home_longitude = home_longitude

    def healthy(self) -> bool:
        return True

    def aircraft(self) -> list[Aircraft]:
        now = time.time()
        definitions = (
            ("406A91", "BAW216", "G-EUYA", "A320", 0.18, 245, 33000, 468, 900),
            ("4CA9C1", "RYR82Q", "EI-ABC", "B738", 0.31, 82, 17400, 312, -640),
            ("400F2B", "EZY48M", "G-EZAA", "A319", 0.46, 155, 9200, 246, 1200),
            ("4841A5", "KLM1017", "PH-EXA", "E190", 0.62, 25, 28100, 438, 0),
            ("3C64F6", "DLH7JM", "D-AIDI", "A321", 0.77, 298, 36500, 482, -128),
        )
        tracks: list[Aircraft] = []
        for index, (hex_code, callsign, registration, aircraft_type, radius, bearing, altitude, speed, climb) in enumerate(definitions):
            moving_bearing = (bearing + now / (36 + index * 7)) % 360
            radians = math.radians(moving_bearing)
            lat = self.home_latitude + math.cos(radians) * radius
            lon_scale = max(math.cos(math.radians(self.home_latitude)), 0.2)
            lon = self.home_longitude + math.sin(radians) * radius / lon_scale
            tracks.append(
                Aircraft(
                    hex=hex_code,
                    callsign=callsign,
                    latitude=round(lat, 5),
                    longitude=round(lon, 5),
                    altitude_ft=altitude,
                    ground_speed_kt=speed,
                    track_deg=round((moving_bearing + 35) % 360),
                    vertical_rate_fpm=climb,
                    registration=registration,
                    aircraft_type=aircraft_type,
                    category="A3",
                    squawk="7000",
                )
            )
        return tracks

    def details(self, hex_code: str) -> dict[str, Any] | None:
        track = next((item for item in self.aircraft() if item.hex == hex_code.upper()), None)
        if track is None:
            return None
        manufacturer, model = describe_aircraft_type(track.aircraft_type)
        return {
            "hex": track.hex,
            "callsign": track.callsign,
            "registration": track.registration,
            "type_code": track.aircraft_type,
            "manufacturer": manufacturer,
            "model": model,
            "operator": describe_operator(track.callsign[:3]),
            "route": {
                "origin": {"code": "LHR", "name": "Heathrow Airport", "location": "London"},
                "destination": {"code": "EDI", "name": "Edinburgh Airport", "location": "Edinburgh"},
                "plausible": True,
            },
        }
