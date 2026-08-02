from __future__ import annotations

import json
from pathlib import Path
import unittest


class AirportDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = Path(__file__).resolve().parents[1] / "frontend" / "data" / "airports-gb.json"
        cls.airports = json.loads(path.read_text(encoding="utf-8"))

    def test_contains_compact_coded_uk_airports(self) -> None:
        self.assertGreater(len(self.airports), 100)
        self.assertLess(len(self.airports), 250)
        self.assertTrue(all(airport["icao"] or airport["iata"] for airport in self.airports))
        codes = {airport["icao"] or airport["iata"] for airport in self.airports}
        self.assertEqual(len(codes), len(self.airports))

    def test_contains_oxford_airport(self) -> None:
        oxford = next(airport for airport in self.airports if airport["iata"] == "OXF")
        self.assertEqual(oxford["icao"], "EGTK")
        self.assertEqual(oxford["type"], "medium")


if __name__ == "__main__":
    unittest.main()
