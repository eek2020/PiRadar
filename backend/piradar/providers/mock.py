from __future__ import annotations

import math
import time

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
            ("406A91", "BAW216", 0.18, 245, 33000, 468, 900),
            ("4CA9C1", "RYR82Q", 0.31, 82, 17400, 312, -640),
            ("400F2B", "EZY48M", 0.46, 155, 9200, 246, 1200),
            ("4841A5", "KLM1017", 0.62, 25, 28100, 438, 0),
            ("3C64F6", "DLH7JM", 0.77, 298, 36500, 482, -128),
        )
        tracks: list[Aircraft] = []
        for index, (hex_code, callsign, radius, bearing, altitude, speed, climb) in enumerate(definitions):
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
                )
            )
        return tracks
