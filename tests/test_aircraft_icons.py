from __future__ import annotations

import unittest

from piradar.aircraft_icons import ICON_FAMILIES, icon_family
from piradar.models import Aircraft


class AircraftIconTests(unittest.TestCase):
    def assertFamily(self, family: str, *type_codes: str) -> None:
        for code in type_codes:
            with self.subTest(code=code):
                self.assertEqual(icon_family(code), family)

    def test_military_types_seen_over_the_uk(self) -> None:
        self.assertFamily("delta", "EUFI", "RFAL", "GRIF")
        self.assertFamily("fighter", "F35", "HAWK", "F16", "TOR")
        self.assertFamily("heavy4", "C17", "E3TF", "K35R", "R135")
        self.assertFamily("airlifter", "A400", "C30J", "C130")
        self.assertFamily("widebody", "A332", "KC46")
        self.assertFamily("tandem", "H47")
        self.assertFamily("tiltrotor", "V22")
        self.assertFamily("helicopter", "H64", "EH10", "LYNX", "PUMA", "EC35", "A139")
        self.assertFamily("drone", "Q9")
        self.assertFamily("twinprop", "B350", "BE20")
        self.assertFamily("bizjet", "E50P", "PC24", "GLF5", "GL5T", "H25B", "HDJT")
        self.assertFamily("light", "G115", "TEX2", "PC21", "TBM7")

    def test_civil_types(self) -> None:
        self.assertFamily("narrowbody", "A319", "A20N", "B738", "B38M", "E190", "CRJ9", "BCS3", "B752")
        self.assertFamily("widebody", "A359", "B77W", "B789", "A310")
        self.assertFamily("heavy4", "B744", "A388")
        self.assertFamily("regional", "AT76", "DH8D", "SF34")
        self.assertFamily("twinprop", "PA31", "DA42", "BN2P", "C421")
        self.assertFamily("light", "C172", "P28A", "SR22", "DA40", "PA28")
        self.assertFamily("glider", "GLID", "ASK21", "DG80", "G109")

    def test_h_prefixed_jets_are_not_helicopters(self) -> None:
        for code in ("HAWK", "H25B", "HDJT"):
            with self.subTest(code=code):
                self.assertNotIn(icon_family(code), {"helicopter", "tandem"})

    def test_falls_back_to_emitter_category(self) -> None:
        self.assertEqual(icon_family("", "A7"), "helicopter")
        self.assertEqual(icon_family("ZZZZ", "A5"), "widebody")
        self.assertEqual(icon_family("", "a1"), "light")
        self.assertEqual(icon_family("", ""), "unknown")

    def test_every_result_is_a_known_family(self) -> None:
        for code in ("EUFI", "C17", "ZZZZ", "", "B738", "H47"):
            self.assertIn(icon_family(code, "A3"), ICON_FAMILIES)

    def test_aircraft_payload_carries_icon(self) -> None:
        track = Aircraft("43C123", "TYPHN1", 53.0, -1.0, 20000, 400, 90, aircraft_type="EUFI")
        self.assertEqual(track.to_dict()["icon"], "delta")


if __name__ == "__main__":
    unittest.main()
