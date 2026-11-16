"""Choose a map silhouette for an aircraft from its ICAO type designator.

The frontend draws one silhouette per family. Families are checked in order,
so specific military and heavy types win over the broad prefix rules below
them; when the type code is unknown the ADS-B emitter category decides.
"""

from __future__ import annotations

import re

ICON_FAMILIES = (
    "heavy4",      # four-engine jets: C-17, E-3, 747, A340
    "widebody",    # twin-aisle twins: A330/Voyager, 767, 777, 787
    "narrowbody",  # single-aisle jets: A320 family, 737, Embraer E-jets
    "airlifter",   # four-turboprop high wing: A400M, C-130
    "regional",    # twin-turboprop airliners: ATR, Dash 8, C295
    "twinprop",    # light twins: King Air, Islander, Seneca
    "bizjet",      # rear-engine jets: Gulfstream, Citation, Phenom
    "delta",       # delta/canard fighters: Typhoon, Rafale, Gripen
    "fighter",     # swept-wing fast jets and jet trainers: F-35, Hawk
    "light",       # single-engine props: Cessna, Tutor, Texan II
    "glider",
    "helicopter",
    "tandem",      # tandem-rotor helicopters: Chinook
    "tiltrotor",   # V-22 Osprey
    "drone",       # MQ-9 Reaper / Protector, RQ-4
    "unknown",
)

_EXACT: dict[str, frozenset[str]] = {
    "heavy4": frozenset({
        "B741", "B742", "B743", "B744", "B748", "B74S", "B74R", "BLCF",
        "A388", "A340", "A342", "A343", "A345", "A346",
        "C17", "C5", "C5M", "C141", "E3TF", "E3CF", "E6", "E8",
        "K35R", "K35E", "R135", "C135", "B52", "B701", "B703", "DC8", "VC10",
        "IL62", "IL76", "IL96", "A124", "A225",
    }),
    "widebody": frozenset({
        "A306", "A30B", "A310", "A332", "A333", "A337", "A338", "A339", "A359", "A35K", "A3ST",
        "B762", "B763", "B764", "B772", "B773", "B77L", "B77W", "B778", "B779",
        "B788", "B789", "B78X", "DC10", "MD11", "L101", "KC46", "IL86",
    }),
    "airlifter": frozenset({"C130", "C30J", "A400", "P3", "P3C", "AN12", "AN22", "L188", "AN70"}),
    "delta": frozenset({"EUFI", "RFAL", "GRIF", "MIR2", "MIRA", "J10", "CONC", "B2"}),
    "fighter": frozenset({
        "F35", "F16", "F15", "F18", "F18H", "F18S", "F22", "F14", "F4", "F5", "F117",
        "TOR", "HAWK", "T38", "T45", "T7", "A10", "AJET", "M346", "L39", "L159", "M339",
        "SU27", "SU30", "SU33", "SU34", "SU35", "SU57", "MG29", "MG31", "JF17", "J20",
        "KF21", "HUNT", "JAGR", "AV8B", "HAR2", "B1", "T50", "FA50",
    }),
    "tandem": frozenset({"H47", "CH47", "H46"}),
    "tiltrotor": frozenset({"V22", "V280"}),
    "helicopter": frozenset({
        "EC20", "EC25", "EC30", "EC35", "EC45", "EC55", "EC75", "H160", "EH10",
        "AS32", "AS3B", "AS50", "AS55", "AS65", "B06", "B06T", "B407", "B412", "B427",
        "B429", "B430", "B47G", "B212", "B222", "B230", "B505", "S76", "S92", "S61",
        "S64", "S70", "H60", "H64", "H53", "H53S", "UH1", "UH1Y", "H1", "A109", "A119",
        "A129", "A139", "A149", "A169", "A189", "LYNX", "PUMA", "NH90", "GAZL", "ALO2",
        "ALO3", "LAMA", "MI8", "MI17", "MI24", "MI26", "MI28", "KA27", "KA32", "KA52",
        "EXPL", "H500", "H269", "EN28", "EN48", "G2CA", "R22", "R44", "R66", "TIGR",
        "BK17", "BO05", "SH09", "HUCO", "S300",
    }),
    "drone": frozenset({"Q9", "Q4", "Q1", "MQ9", "MQ4", "RQ4", "GLHK", "HRON"}),
    "glider": frozenset({"G103", "G109", "U2"}),
    "light": frozenset({"TEX2", "G115", "PC21", "PC7", "PC9", "TUCA", "PC12", "C208"}),
}

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("glider", re.compile(r"^(GLID|ASW|ASK|ASH|ASG|DG\d|LS\d|SZD|VENT|DUOD|JANU|NIMB|DISC|ARCU|ARCP)")),
    ("bizjet", re.compile(
        r"^(GLF\d|GL\dT|GLEX|CL[36]\d|C25[ABCM]|C5[0-6]\d|C56X|C6[58]\w|C7[05]0|E35L|E5[05]P|E545|E550"
        r"|LJ\d\d|F2TH|F900|FA\d[0X]|FA[78]X|H25[ABC]|HDJT|BE40|PRM1|ASTR|GALX|G150|G200|G280"
        r"|PC24|SF50|EA50|GA\dC)$"
    )),
    ("narrowbody", re.compile(
        r"^(A3[12]\d|A[12][019]N|B7[123]\d|B3[789X]M|B75[23]|MD[89]\d|DC9\d?|E1[79]\d|E7[05][LS]"
        r"|E29\d|CRJ[\dX]|BCS[13]|F70|F100|B46[123]|RJ70|RJ85|RJ1H|SU95|C919|P8|E135|E145)$"
    )),
    ("regional", re.compile(
        r"^(AT[4-7]\d|ATP|DH8[A-D]|SF34|SB20|JS3\d|JS41|D328|E120|F27|F50|DHC7|SH3[36]|L410|L610"
        r"|AN2[46]|AN32|Y12|MA60|C212|CN35|C295|C27J|D228|C160)$"
    )),
    ("twinprop", re.compile(
        r"^(BE[23]0|B350|BE9[LT]|BE10|BE99|BE[5-9]\d|C3[0-4]\d|C4[0-4]\d|PA3[14]|PA44|PA23|PA60"
        r"|P68|DA42|DA62|BN2\w|DHC6|MU2|P180|AC\d\d|AEST)$"
    )),
    ("light", re.compile(r"^(C1|C2|P28|PA|BE|DA|SR|M20|TB|PC|RV\d|DR\d|AA5|TOBA|TAMP|PIVI|EV97|EUPA)")),
)

_CATEGORY_FALLBACK = {
    "A1": "light",
    "A2": "bizjet",
    "A3": "narrowbody",
    "A4": "narrowbody",
    "A5": "widebody",
    "A6": "fighter",
    "A7": "helicopter",
    "B1": "glider",
    "B4": "light",
    "B6": "drone",
}


def icon_family(type_code: str, category: str = "") -> str:
    """Return the silhouette family for an ICAO type designator."""
    code = type_code.strip().upper()
    if code:
        for family, codes in _EXACT.items():
            if code in codes:
                return family
        for family, pattern in _PATTERNS:
            if pattern.match(code):
                return family
    return _CATEGORY_FALLBACK.get(category.strip().upper(), "unknown")
