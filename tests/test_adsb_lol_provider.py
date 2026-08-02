from __future__ import annotations

import json
import unittest

from piradar.providers.adsb_lol import AdsbLolProvider


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class AdsbLolProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = 100.0
        self.calls = 0
        self.payload = {
            "ac": [
                {
                    "hex": "406a91",
                    "flight": " BAW216 ",
                    "lat": 52.3,
                    "lon": -0.8,
                    "alt_baro": 32000,
                    "gs": 451.6,
                    "track": 361.2,
                    "baro_rate": -640,
                    "r": "G-EUYA",
                    "t": "A320",
                    "category": "A3",
                    "squawk": "1234",
                },
                {"hex": "abc123", "lat": None, "lon": 0},
                {
                    "hex": "4ca9c1",
                    "r": "EI-ABC",
                    "lat": "52.1",
                    "lon": "-1.0",
                    "alt_baro": "ground",
                },
            ]
        }

    def opener(self, request: object, timeout: int) -> FakeResponse:
        self.calls += 1
        self.assertEqual(timeout, 12)
        return FakeResponse(self.payload)

    def provider(self) -> AdsbLolProvider:
        return AdsbLolProvider(
            52.2,
            -0.9,
            50,
            opener=self.opener,
            monotonic=lambda: self.now,
        )

    def test_normalizes_aircraft_and_ground_altitude(self) -> None:
        provider = self.provider()
        aircraft = provider.aircraft()
        self.assertEqual(len(aircraft), 2)
        self.assertEqual(aircraft[0].callsign, "BAW216")
        self.assertEqual(aircraft[0].track_deg, 1)
        self.assertEqual(aircraft[0].registration, "G-EUYA")
        self.assertEqual(aircraft[0].aircraft_type, "A320")
        self.assertEqual(aircraft[0].squawk, "1234")
        self.assertEqual(aircraft[1].callsign, "EI-ABC")
        self.assertEqual(aircraft[1].altitude_ft, 0)
        self.assertEqual(provider.status, "live")

    def test_caches_successful_response(self) -> None:
        provider = self.provider()
        provider.aircraft()
        provider.aircraft()
        self.assertEqual(self.calls, 1)
        self.now += 9
        provider.aircraft()
        self.assertEqual(self.calls, 2)

    def test_returns_stale_cache_after_failure(self) -> None:
        provider = self.provider()
        original = provider.aircraft()
        self.now += 9

        def fail(request: object, timeout: int) -> FakeResponse:
            raise OSError("network unavailable")

        provider._opener = fail
        self.assertEqual(provider.aircraft(), original)
        self.assertEqual(provider.status, "stale")
        self.assertFalse(provider.healthy())

    def test_reports_offline_before_first_success(self) -> None:
        def fail(request: object, timeout: int) -> FakeResponse:
            raise OSError("network unavailable")

        provider = AdsbLolProvider(0, 0, 10, opener=fail)
        self.assertEqual(provider.aircraft(), [])
        self.assertEqual(provider.status, "offline")

    def test_enriches_and_caches_selected_aircraft(self) -> None:
        route_calls = 0

        def opener(request: object, timeout: int) -> FakeResponse:
            nonlocal route_calls
            if "/api/0/route/" in request.full_url:  # type: ignore[attr-defined]
                route_calls += 1
                self.assertEqual(timeout, 8)
                return FakeResponse(
                    {
                        "airline_code": "BAW",
                        "airport_codes": "EGLL-KJFK",
                        "plausible": True,
                        "_airports": [
                            {"iata": "LHR", "name": "Heathrow Airport", "location": "London"},
                            {"iata": "JFK", "name": "John F Kennedy Airport", "location": "New York"},
                        ],
                    }
                )
            return FakeResponse(self.payload)

        provider = AdsbLolProvider(52.2, -0.9, 50, opener=opener, monotonic=lambda: self.now)
        details = provider.details("406a91")
        self.assertIsNotNone(details)
        assert details is not None
        self.assertEqual(details["manufacturer"], "Airbus")
        self.assertEqual(details["model"], "A320")
        self.assertEqual(details["operator"], "British Airways")
        self.assertEqual(details["route"]["origin"]["code"], "LHR")
        self.assertEqual(details["route"]["destination"]["code"], "JFK")
        self.assertEqual(provider.details("406A91"), details)
        self.assertEqual(route_calls, 1)


if __name__ == "__main__":
    unittest.main()
