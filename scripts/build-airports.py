#!/usr/bin/env python3
"""Build the compact UK airport layer from an OurAirports airports.csv file."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys


ALLOWED_TYPES = {"small_airport", "medium_airport", "large_airport"}


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: build-airports.py INPUT.csv OUTPUT.json")

    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    airports: list[dict[str, object]] = []
    with source.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["iso_country"] != "GB" or row["type"] not in ALLOWED_TYPES:
                continue
            if not (row["icao_code"] or row["iata_code"]):
                continue
            airports.append(
                {
                    "icao": row["icao_code"],
                    "iata": row["iata_code"],
                    "name": row["name"],
                    "latitude": round(float(row["latitude_deg"]), 6),
                    "longitude": round(float(row["longitude_deg"]), 6),
                    "type": row["type"].removesuffix("_airport"),
                }
            )

    airports.sort(key=lambda airport: (str(airport["iata"] or airport["icao"]), str(airport["name"])))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(airports, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(airports)} airports to {destination}")


if __name__ == "__main__":
    main()
