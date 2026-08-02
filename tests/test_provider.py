from __future__ import annotations

import unittest

from piradar.providers.mock import MockAircraftProvider


class MockProviderTests(unittest.TestCase):
    def test_returns_normalized_unique_tracks(self) -> None:
        provider = MockAircraftProvider(51.5, -0.1)
        aircraft = provider.aircraft()
        self.assertEqual(len(aircraft), 5)
        self.assertEqual(len({track.hex for track in aircraft}), len(aircraft))
        for track in aircraft:
            self.assertTrue(-90 <= track.latitude <= 90)
            self.assertTrue(-180 <= track.longitude <= 180)
            self.assertTrue(0 <= track.track_deg < 360)

    def test_is_always_healthy(self) -> None:
        self.assertTrue(MockAircraftProvider(0, 0).healthy())


if __name__ == "__main__":
    unittest.main()

