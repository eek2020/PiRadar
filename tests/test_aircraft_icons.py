from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

from piradar.aircraft_icons import ICONS, icon_family
from piradar.models import Aircraft

ROOT = Path(__file__).resolve().parents[1]


class AircraftIconTests(unittest.TestCase):
    def assertIcon(self, icon: str, *type_codes: str) -> None:
        for code in type_codes:
            with self.subTest(code=code):
                self.assertEqual(icon_family(code), icon)

    def test_military_types_seen_over_the_uk(self) -> None:
        self.assertIcon("typhoon", "EUFI")
        self.assertIcon("rafale", "RFAL", "GRIF")
        self.assertIcon("f35", "F35")
        self.assertIcon("hawk", "HAWK", "T45")
        self.assertIcon("fighter", "F16", "F15", "TOR")
        self.assertIcon("apache", "H64")
        self.assertIcon("merlin", "EH10", "LYNX", "PUMA", "H60")
        self.assertIcon("chinook", "H47")
        self.assertIcon("c130", "C30J", "C130")
        self.assertIcon("c17", "C17")
        self.assertIcon("a400m", "A400")
        self.assertIcon("osprey", "V22")
        self.assertIcon("a340", "E3TF", "K35R", "R135")
        self.assertIcon("a330", "A332")
        self.assertIcon("beechcraft", "B350", "BE20")
        self.assertIcon("learjet", "E50P", "PC24", "H25B", "HDJT")
        self.assertIcon("cessna", "G115", "TEX2", "PC21", "TBM7")
        self.assertIcon("b1", "Q9")

    def test_civil_types(self) -> None:
        self.assertIcon("a320", "A319", "A20N", "A321", "BCS3")
        self.assertIcon("b737", "B738", "B38M", "B752")
        self.assertIcon("b747", "B744", "B748")
        self.assertIcon("a380", "A388")
        self.assertIcon("b787", "B789", "A359")
        self.assertIcon("b777", "B77W")
        self.assertIcon("e195", "E190", "E75L")
        self.assertIcon("crjx", "CRJ9")
        self.assertIcon("dh8a", "AT76", "DH8D")
        self.assertIcon("glf5", "GLF5", "GL5T", "CL60")
        self.assertIcon("fa7x", "FA7X", "F900")
        self.assertIcon("cessna", "C172", "P28A", "SR22", "DA40")
        self.assertIcon("a7", "EC35", "A139", "R44")
        self.assertIcon("b1", "GLID", "ASK21", "G109")

    def test_h_prefixed_jets_are_not_helicopters(self) -> None:
        for code in ("HAWK", "H25B", "HDJT"):
            with self.subTest(code=code):
                self.assertNotIn(icon_family(code), {"a7", "apache", "merlin", "chinook"})

    def test_falls_back_to_emitter_category(self) -> None:
        self.assertEqual(icon_family("", "A7"), "a7")
        self.assertEqual(icon_family("ZZZZ", "A5"), "a5")
        self.assertEqual(icon_family("", "a1"), "a1")
        self.assertEqual(icon_family("", ""), "a0")

    def test_every_icon_has_an_asset(self) -> None:
        assets = {path.stem for path in (ROOT / "assets" / "aircraft-icons").glob("*/*.svg")}
        self.assertEqual(ICONS - assets, set())

    def test_bundle_matches_assets(self) -> None:
        bundle = ROOT / "frontend" / "aircraft-shapes.js"
        before = bundle.read_text(encoding="utf-8")
        try:
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build-aircraft-icons.py")],
                check=True,
                capture_output=True,
            )
            rebuilt = bundle.read_text(encoding="utf-8")
        finally:
            bundle.write_text(before, encoding="utf-8")
        self.assertEqual(before, rebuilt, "run scripts/build-aircraft-icons.py")
        shapes = json.loads(before[before.index("{"): before.rindex("}") + 1])
        self.assertEqual(ICONS - set(shapes), set())

    def test_aircraft_payload_carries_icon(self) -> None:
        track = Aircraft("43C123", "TYPHN1", 53.0, -1.0, 20000, 400, 90, aircraft_type="EUFI")
        self.assertEqual(track.to_dict()["icon"], "typhoon")


if __name__ == "__main__":
    unittest.main()
