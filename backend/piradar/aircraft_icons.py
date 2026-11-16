"""Choose a map icon for an aircraft from its ICAO type designator.

Icon names match the SVG files in ``assets/aircraft-icons`` (bundled into
``frontend/aircraft-shapes.js`` by ``scripts/build-aircraft-icons.py``).
Specific types are matched first, then broad prefix rules; when the type code
is unknown the ADS-B emitter category picks a generic icon.
"""

from __future__ import annotations

import re

# Icon name -> ICAO type designators drawn with it.
_EXACT: dict[str, frozenset[str]] = {
    # Military, from PiRadar's own silhouettes
    "typhoon": frozenset({"EUFI"}),
    "rafale": frozenset({"RFAL", "GRIF", "MIR2", "MIRA", "J10"}),
    "f35": frozenset({"F35", "F22", "J20", "SU57", "KF21"}),
    "hawk": frozenset({
        "HAWK", "T45", "AJET", "M346", "L39", "L159", "M339", "T38", "T7", "T50", "YK130",
    }),
    "apache": frozenset({"H64", "A129", "TIGR", "H1", "KA52", "MI28"}),
    "merlin": frozenset({
        "EH10", "H60", "S70", "S92", "S61", "NH90", "PUMA", "AS32", "LYNX", "H53", "H53S",
        "MI8", "MI17", "MI24", "MI26", "KA27", "KA32",
    }),
    "chinook": frozenset({"H47", "CH47", "H46"}),
    "c130": frozenset({"C130", "C30J", "P3", "P3C", "AN12", "L188"}),
    "c17": frozenset({"C17", "C5", "C5M", "C141", "IL76", "A124", "A225"}),
    "a400m": frozenset({"A400", "AN22", "AN70"}),
    "osprey": frozenset({"V22", "V280", "B609", "A609"}),
    # Civil and other military, from the ADS-B Radar set
    "fighter": frozenset({
        "F16", "F15", "F18", "F18H", "F18S", "F14", "F4", "F5", "F117", "TOR", "SU27",
        "SU30", "SU33", "SU34", "SU35", "MG29", "MG31", "JF17", "HUNT", "JAGR", "AV8B", "HAR2",
    }),
    "a340": frozenset({
        "A340", "A342", "A343", "A345", "A346", "E3TF", "E3CF", "E6", "E8", "K35R", "K35E",
        "R135", "C135", "B701", "B703", "DC8", "VC10", "IL62", "B52",
    }),
    "a380": frozenset({"A388"}),
    "b747": frozenset({"B741", "B742", "B743", "B744", "B748", "B74S", "B74R", "BLCF"}),
    "a330": frozenset({"A306", "A30B", "A310", "A332", "A333", "A337", "A338", "A339", "A3ST"}),
    "b767": frozenset({"B762", "B763", "B764", "KC46"}),
    "b777": frozenset({"B772", "B773", "B77L", "B77W", "B778", "B779"}),
    "b787": frozenset({"B788", "B789", "B78X", "A359", "A35K"}),
    "md11": frozenset({"MD11", "DC10", "L101"}),
    "fa7x": frozenset({"FA7X", "FA8X", "F900", "FA50"}),
    "cessna": frozenset({"TEX2", "G115", "PC21", "PC7", "PC9", "TUCA", "PC12", "C208"}),
    "b1": frozenset({"G103", "G109", "U2", "Q9", "MQ9", "Q4", "RQ4", "GLHK", "HRON"}),
    "a7": frozenset({
        "EC20", "EC25", "EC30", "EC35", "EC45", "EC55", "EC75", "H160", "AS3B", "AS50",
        "AS55", "AS65", "B06", "B06T", "B407", "B412", "B427", "B429", "B430", "B47G",
        "B212", "B222", "B230", "B505", "S76", "S64", "UH1", "UH1Y", "A109", "A119",
        "A139", "A149", "A169", "A189", "GAZL", "ALO2", "ALO3", "LAMA", "EXPL", "H500",
        "H269", "EN28", "EN48", "G2CA", "R22", "R44", "R66", "BK17", "BO05", "SH09",
        "HUCO", "S300",
    }),
}

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("b1", re.compile(r"^(GLID|ASW|ASK|ASH|ASG|DG\d|LS\d|SZD|VENT|DUOD|JANU|NIMB|DISC|ARCU|ARCP)")),
    ("glf5", re.compile(r"^(GLF\d|GL\dT|GLEX|CL[36]\d|G150|G200|G280|GALX|GA\dC)$")),
    ("learjet", re.compile(
        r"^(LJ\d\d|C25[ABCM]|C5[0-6]\d|C56X|C6[58]\w|C7[05]0|E35L|E5[05]P|E545|E550|F2TH"
        r"|FA10|FA20|H25[ABC]|HDJT|BE40|PRM1|ASTR|PC24|SF50|EA50)$"
    )),
    ("a320", re.compile(r"^(A3[12]\d|A[12][019]N|BCS[13]|C919)$")),
    ("b737", re.compile(r"^(B73\d|B3[789X]M|B75[23]|P8)$")),
    ("e195", re.compile(r"^(E1[79]\d|E7[05][LS]|E29\d)$")),
    ("erj", re.compile(r"^(E135|E145|E14\d)$")),
    ("crjx", re.compile(r"^(CRJ[\dX])$")),
    ("f100", re.compile(r"^(F70|F100|B712|B717|MD[89]\d|DC9\d?|B46[123]|RJ70|RJ85|RJ1H|SU95)$")),
    ("dh8a", re.compile(
        r"^(AT[4-7]\d|ATP|DH8[A-D]|SF34|SB20|JS3\d|JS41|D328|E120|F27|F50|DHC7|SH3[36]|L410"
        r"|L610|AN2[46]|AN32|Y12|MA60|C212|CN35|C295|C27J|D228|C160)$"
    )),
    ("beechcraft", re.compile(
        r"^(BE[23]0|B350|BE9[LT]|BE10|BE99|BE[5-9]\d|C3[0-4]\d|C4[0-4]\d|PA3[14]|PA44|PA23"
        r"|PA60|P68|DA42|DA62|BN2\w|DHC6|MU2|P180|AC\d\d|AEST)$"
    )),
    ("cessna", re.compile(r"^(C1|C2|P28|PA|BE|DA|SR|M20|TB|PC|RV\d|DR\d|AA5|TOBA|TAMP|PIVI|EV97|EUPA)")),
)

# ADS-B emitter category -> the ADS-B Radar generic icon for that class.
_CATEGORY_FALLBACK = {
    "A1": "a1",
    "A2": "a2",
    "A3": "a3",
    "A4": "a4",
    "A5": "a5",
    "A6": "a6",
    "A7": "a7",
    "B1": "b1",
    "B4": "a1",
    "B6": "b1",
}

ICONS = frozenset(_EXACT) | {name for name, _ in _PATTERNS} | frozenset(_CATEGORY_FALLBACK.values()) | {"a0"}


def icon_family(type_code: str, category: str = "") -> str:
    """Return the icon name for an ICAO type designator."""
    code = type_code.strip().upper()
    if code:
        for icon, codes in _EXACT.items():
            if code in codes:
                return icon
        for icon, pattern in _PATTERNS:
            if pattern.match(code):
                return icon
    return _CATEGORY_FALLBACK.get(category.strip().upper(), "a0")
