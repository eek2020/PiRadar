from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
import gzip
import json
import math
import threading
import time
import zlib
from typing import Any
from urllib.request import Request, urlopen
from urllib.parse import quote

from piradar.aircraft_types import describe_aircraft_type, describe_operator
from piradar.models import Aircraft
from piradar.storage import EnrichmentCache

# readsb/adsb.lol database flag bit for military airframes.
MILITARY_FLAG = 1
MILITARY_URL = "https://api.adsb.lol/v2/mil"
REQUEST_HEADERS = {
    "Accept": "application/json",
    # Compressed responses are roughly 4-5x smaller, which matters most on 4G.
    "Accept-Encoding": "gzip",
    "User-Agent": "PiRadar/0.1",
}


@dataclass(slots=True)
class _Feed:
    url: str
    aircraft: list[Aircraft] = field(default_factory=list)
    last_attempt: float = float("-inf")
    has_succeeded: bool = False
    last_error: str | None = None


class AdsbLolProvider:
    """Internet-fed aircraft positions from the adsb.lol v2 API.

    Two feeds are kept separately and only the one being displayed is fetched:
    the local area feed (all traffic within ``range_nm``) and the military feed
    (adsb.lol's worldwide military list, trimmed to ``military_range_nm``).
    """

    name = "adsb.lol"

    def __init__(
        self,
        home_latitude: float,
        home_longitude: float,
        range_nm: int,
        refresh_seconds: int = 8,
        *,
        military_range_nm: int = 400,
        opener: Callable[..., Any] = urlopen,
        monotonic: Callable[[], float] = time.monotonic,
        cache: EnrichmentCache | None = None,
    ) -> None:
        self.home_latitude = home_latitude
        self.home_longitude = home_longitude
        self.military_range_nm = military_range_nm
        self.url = (
            f"https://api.adsb.lol/v2/lat/{home_latitude}"
            f"/lon/{home_longitude}/dist/{range_nm}"
        )
        self.refresh_seconds = refresh_seconds
        self._opener = opener
        self._monotonic = monotonic
        self._cache = cache
        self._lock = threading.Lock()
        self._feeds = {False: _Feed(self.url), True: _Feed(MILITARY_URL)}
        self._active = False
        self._details_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @property
    def status(self) -> str:
        feed = self._feeds[self._active]
        if feed.last_error is not None:
            return "stale" if feed.has_succeeded else "offline"
        return "live" if feed.has_succeeded else "starting"

    def healthy(self) -> bool:
        return self.status in {"starting", "live"}

    def aircraft(self, military: bool = False) -> list[Aircraft]:
        with self._lock:
            self._active = military
            feed = self._feeds[military]
            now = self._monotonic()
            if now - feed.last_attempt < self.refresh_seconds:
                return list(feed.aircraft)
            feed.last_attempt = now

            try:
                tracks = self._normalize(self._fetch_json(feed.url, timeout=12))
                if military:
                    tracks = [
                        track
                        for track in tracks
                        if distance_nm(
                            self.home_latitude,
                            self.home_longitude,
                            track.latitude,
                            track.longitude,
                        )
                        <= self.military_range_nm
                    ]
                feed.aircraft = tracks
                feed.has_succeeded = True
                feed.last_error = None
            except (AttributeError, OSError, ValueError, TypeError, KeyError) as error:
                feed.last_error = f"{type(error).__name__}: {error}"

            return list(feed.aircraft)

    def _cached_track(self, hex_code: str) -> Aircraft | None:
        with self._lock:
            active = self._feeds[self._active].aircraft
            other = self._feeds[not self._active].aircraft
            return next((item for item in (*active, *other) if item.hex == hex_code), None)

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
                    military=bool(int(cls._number(item.get("dbFlags"), 0) or 0) & MILITARY_FLAG),
                )
            )
        # Keep military tracks if a busy area exceeds the display cap.
        normalized.sort(key=lambda track: not track.military)
        return normalized[:250]

    def details(self, hex_code: str) -> dict[str, Any] | None:
        normalized_hex = hex_code.strip().upper()
        self.aircraft(self._active)
        track = self._cached_track(normalized_hex)
        if track is None:
            return None

        cache_key = f"{track.hex}:{track.callsign}"
        persistent_key = ":".join(
            (
                datetime.now(UTC).date().isoformat(),
                track.hex,
                track.registration or "-",
                track.callsign,
            )
        )
        now = self._monotonic()
        cached = self._details_cache.get(cache_key)
        if cached:
            cache_seconds = 3600 if cached[1].get("route") else 20
            if now - cached[0] < cache_seconds:
                return dict(cached[1])
        if self._cache:
            persistent = self._cache.get("flight_details", persistent_key)
            if persistent is not None:
                self._details_cache[cache_key] = (now, persistent)
                return dict(persistent)

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
            route_payload: dict[str, Any] = {}
            try:
                route_payload = self._fetch_json(route_url, timeout=8)
            except (AttributeError, OSError, ValueError, TypeError, KeyError):
                fallback_url = (
                    "https://vrs-standing-data.adsb.lol/routes/"
                    f"{quote(callsign[:2], safe='')}/{quote(callsign, safe='')}.json"
                )
                try:
                    route_payload = self._fetch_json(fallback_url, timeout=8)
                except (AttributeError, OSError, ValueError, TypeError, KeyError):
                    route_payload = {}

            details["operator"] = describe_operator(str(route_payload.get("airline_code") or ""))
            airports = route_payload.get("_airports") or []
            if len(airports) >= 2 and route_payload.get("airport_codes") != "unknown":
                details["route"] = {
                    "origin": self._airport(airports[0]),
                    "destination": self._airport(airports[-1]),
                    "plausible": bool(route_payload.get("plausible", False)),
                }

        self._details_cache[cache_key] = (now, details)
        if self._cache:
            self._cache.set(
                "flight_details",
                persistent_key,
                details,
                ttl_seconds=21600 if details.get("route") else 120,
            )
        return dict(details)

    def _fetch_json(self, url: str, *, timeout: int) -> Any:
        request = Request(url, headers=REQUEST_HEADERS)
        with self._opener(request, timeout=timeout) as response:
            body = response.read()
        if body[:2] == b"\x1f\x8b":
            try:
                body = gzip.decompress(body)
            except zlib.error as error:
                raise ValueError(f"corrupt gzip response: {error}") from error
        return json.loads(body)

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


def distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * 3440.065 * math.asin(min(1.0, math.sqrt(a)))
