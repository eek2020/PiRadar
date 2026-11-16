from __future__ import annotations

import unittest

from piradar.providers.mock import MockAircraftProvider


class MockProviderTests(unittest.TestCase):
    def test_returns_normalized_unique_tracks(self) -> None:
        provider = MockAircraftProvider(51.5, -0.1)
        aircraft = provider.aircraft()
        self.assertEqual(len(aircraft), 6)
        self.assertEqual(len({track.hex for track in aircraft}), len(aircraft))
        for track in aircraft:
            self.assertTrue(-90 <= track.latitude <= 90)
            self.assertTrue(-180 <= track.longitude <= 180)
            self.assertTrue(0 <= track.track_deg < 360)

    def test_military_mode_returns_only_military_tracks(self) -> None:
        provider = MockAircraftProvider(51.5, -0.1)
        military = provider.aircraft(military=True)
        self.assertEqual([track.hex for track in military], ["43C6F2"])
        self.assertTrue(all(track.military for track in military))
        self.assertEqual(sum(track.military for track in provider.aircraft()), 1)

    def test_is_always_healthy(self) -> None:
        provider = MockAircraftProvider(0, 0)
        self.assertTrue(provider.healthy())
        self.assertEqual(provider.status, "live")


if __name__ == "__main__":
    unittest.main()
