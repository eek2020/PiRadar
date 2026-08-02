from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.request import Request, urlopen
from urllib.parse import quote

from piradar.aircraft_types import describe_aircraft_type
from piradar.models import Aircraft


class AdsbLolProvider:
    """Internet-fed aircraft positions from the adsb.lol v2 API."""

    name = "adsb.lol"

    def __init__(
        self,
        home_latitude: float,
        home_longitude: float,
        range_nm: int,
        refresh_seconds: int = 8,
        *,
        opener: Callable[..., Any] = urlopen,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.url = (
            f"https://api.adsb.lol/v2/lat/{home_latitude}"
            f"/lon/{home_longitude}/dist/{range_nm}"
        )
        self.refresh_seconds = refresh_seconds
        self._opener = opener
        self._monotonic = monotonic
        self._lock = threading.Lock()
        self._aircraft: list[Aircraft] = []
        self._last_attempt = float("-inf")
        self._has_succeeded = False
        self._last_error: str | None = None
        self._details_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @property
    def status(self) -> str:
        if self._last_error is not None:
            return "stale" if self._has_succeeded else "offline"
        return "live" if self._has_succeeded else "starting"

    def healthy(self) -> bool:
        return self.status in {"starting", "live"}

    def aircraft(self) -> list[Aircraft]:
        with self._lock:
            now = self._monotonic()
            if now - self._last_attempt < self.refresh_seconds:
                return list(self._aircraft)
            self._last_attempt = now

            request = Request(
                self.url,
                headers={"Accept": "application/json", "User-Agent": "PiRadar/0.1"},
            )
            try:
                with self._opener(request, timeout=12) as response:
                    payload = json.loads(response.read())
                self._aircraft = self._normalize(payload)
                self._has_succeeded = True
                self._last_error = None
            except (AttributeError, OSError, ValueError, TypeError, KeyError) as error:
                self._last_error = f"{type(error).__name__}: {error}"

            return list(self._aircraft)

    @classmethod
    def _normalize(cls, payload: dict[str, Any]) -> list[Aircraft]:
        normalized: list[Aircraft] = []
        for item in payload.get("ac", []):
            latitude = cls._number(item.get("lat"))
            longitude = cls._number(item.get("lon"))
            if latitude is None or longitude is None:
                continue

            hex_code = str(item.get("hex") or "UNKNOWN").upper()
            callsign = str(item.get("flight") or "").strip()
            registration = str(item.get("r") or "").strip()
            altitude = item.get("alt_baro")
            if altitude == "ground":
                altitude_ft = 0
            else:
                altitude_ft = round(
                    cls._number(altitude, cls._number(item.get("alt_geom"), 0)) or 0
                )

            normalized.append(
                Aircraft(
                    hex=hex_code,
                    callsign=callsign or registration or hex_code,
                    latitude=latitude,
                    longitude=longitude,
                    altitude_ft=altitude_ft,
                    ground_speed_kt=round(cls._number(item.get("gs"), 0) or 0),
                    track_deg=round(cls._number(item.get("track"), 0) or 0) % 360,
                    vertical_rate_fpm=round(
                        cls._number(
                            item.get("baro_rate"),
                            cls._number(item.get("geom_rate"), 0),
                        )
                        or 0
                    ),
                    registration=registration,
                    aircraft_type=str(item.get("t") or "").strip().upper(),
                    category=str(item.get("category") or "").strip().upper(),
                    squawk=str(item.get("squawk") or "").strip(),
                )
            )
        return normalized[:250]

    def details(self, hex_code: str) -> dict[str, Any] | None:
        normalized_hex = hex_code.strip().upper()
        track = next((item for item in self.aircraft() if item.hex == normalized_hex), None)
        if track is None:
            return None

        cache_key = f"{track.hex}:{track.callsign}"
        now = self._monotonic()
        cached = self._details_cache.get(cache_key)
        if cached and now - cached[0] < 3600:
            return dict(cached[1])

        manufacturer, model = describe_aircraft_type(track.aircraft_type)
        details: dict[str, Any] = {
            "hex": track.hex,
            "callsign": track.callsign,
            "registration": track.registration,
            "type_code": track.aircraft_type,
            "manufacturer": manufacturer,
            "model": model,
            "operator": "",
            "route": None,
        }

        callsign = track.callsign.strip().upper()
        if callsign and callsign != track.hex and callsign != track.registration.upper():
            route_url = (
                "https://api.adsb.lol/api/0/route/"
                f"{quote(callsign, safe='')}/{track.latitude}/{track.longitude}"
            )
            request = Request(
                route_url,
                headers={"Accept": "application/json", "User-Agent": "PiRadar/0.1"},
            )
            try:
                with self._opener(request, timeout=8) as response:
                    route_payload = json.loads(response.read())
                details["operator"] = str(route_payload.get("airline_code") or "")
                airports = route_payload.get("_airports") or []
                if len(airports) >= 2 and route_payload.get("airport_codes") != "unknown":
                    details["route"] = {
                        "origin": self._airport(airports[0]),
                        "destination": self._airport(airports[-1]),
                        "plausible": bool(route_payload.get("plausible", False)),
                    }
            except (AttributeError, OSError, ValueError, TypeError, KeyError):
                pass

        self._details_cache[cache_key] = (now, details)
        return dict(details)

    @staticmethod
    def _airport(payload: dict[str, Any]) -> dict[str, str]:
        return {
            "code": str(payload.get("iata") or payload.get("icao") or "").upper(),
            "name": str(payload.get("name") or ""),
            "location": str(payload.get("location") or ""),
        }

    @staticmethod
    def _number(value: Any, default: float | None = None) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
