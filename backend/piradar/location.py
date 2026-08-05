from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class PostcodeGeocoder:
    """Resolve UK postcodes without exposing the lookup service to the browser."""

    def __init__(self, *, opener: Callable[..., Any] = urlopen) -> None:
        self._opener = opener

    def lookup(self, postcode: str) -> dict[str, Any]:
        compact = re.sub(r"\s+", "", postcode).upper()
        if not re.fullmatch(r"[A-Z0-9]{5,7}", compact) or not re.search(r"\d[A-Z]{2}$", compact):
            raise ValueError("enter a complete UK postcode")

        request = Request(
            f"https://api.postcodes.io/postcodes/{quote(compact, safe='')}",
            headers={"Accept": "application/json", "User-Agent": "PiRadar/0.1"},
        )
        try:
            with self._opener(request, timeout=8) as response:
                payload = json.loads(response.read())
        except HTTPError as error:
            if error.code == 404:
                raise ValueError("postcode not found") from error
            raise ValueError("postcode lookup unavailable") from error
        except (OSError, URLError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("postcode lookup unavailable") from error

        result = payload.get("result") if isinstance(payload, dict) else None
        if not isinstance(result, dict):
            raise ValueError("postcode not found")
        latitude = result.get("latitude")
        longitude = result.get("longitude")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            raise ValueError("postcode has no usable coordinates")
        return {
            "postcode": str(result.get("postcode") or compact).strip().upper(),
            "latitude": float(latitude),
            "longitude": float(longitude),
        }
