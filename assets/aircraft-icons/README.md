# Aircraft map icons

PiRadar draws each aircraft with a silhouette chosen from its ICAO type code
(`backend/piradar/aircraft_icons.py`). The SVGs here are the sources;
`scripts/build-aircraft-icons.py` bundles them into `frontend/aircraft-shapes.js`.
Run it after adding or changing an icon. The map recolours every icon by
altitude, so only the outline matters; fills and strokes in the files are ignored.

## `adsb-radar/` — civil airliners, business jets, light aircraft, generic classes

Icons by ADS-B Radar for macOS - https://adsb-radar.com - https://apps.apple.com/app/id1538149835

Free for personal and commercial use; the only requirement is this backlink
(https://www.adsb-radar.com/help/icons.html). Files are unmodified copies from
the "Free Aircraft SVG Icon Package". `a0`–`a7` and `b1` are the generic icons for
ADS-B emitter categories (for example `a7` rotorcraft, `b1` glider).

## `piradar/` — military types

Typhoon, Rafale, F-35, Hawk, Apache, Merlin, Chinook, C-130, C-17, A400M and
Osprey, created for PiRadar. `source-silhouettes.png` is the original artwork;
the SVGs were traced from it with `scripts/trace-aircraft-silhouettes.py`.
Licensed with the rest of PiRadar (MIT).
