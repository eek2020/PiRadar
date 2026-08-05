# PiRadar

PiRadar is a dedicated Raspberry Pi aircraft-radar appliance designed to boot directly into a polished, full-screen airspace display.

The first release will use an online ADS-B data provider. Its architecture deliberately supports a later local 1090 MHz receiver using an RTL-SDR and `readsb`, without replacing the user interface.

> PiRadar is an informational display, not a complete or safety-critical source of aircraft information.

## Current status

PiRadar is in active hardware-alpha development. The repository contains the
working Python service, mock and live adsb.lol providers, an 800×480 touch-first
map, persistent settings, and Raspberry Pi kiosk installation support. The
reference Raspberry Pi 3B, Debian 13, HDMI display, touch controller, and
Chromium/Wayland kiosk route have been proven; a reproducible release image and
long-running appliance validation are still in progress.

## Try it

PiRadar requires Python 3.11 or newer. The development server uses only the
Python standard library. Live aircraft, map tiles, and postcode lookup require
internet access; the appliance Wi-Fi control additionally requires
NetworkManager's `nmcli` command.

```bash
./scripts/run-dev.sh
```

Open [http://localhost:8080](http://localhost:8080). Configure another location or range by copying `config/piradar.example.json` to the ignored `config/piradar.json`, editing it, and running:

```bash
PIRADAR_CONFIG=config/piradar.json ./scripts/run-dev.sh
```

Set `"provider": "adsb_lol"` in the local configuration to request live nearby-aircraft positions. Keep `mock` for development, demonstrations and fault isolation. The public adsb.lol service is free and ODbL-licensed, but its operator asks production users to make contact before relying on it.

Run the tests with:

```bash
PYTHONPATH=backend python3 -m unittest discover -s tests -v
```

## Repository guide

| Path | Purpose |
|---|---|
| `backend/` | Python service, domain model and providers |
| `frontend/` | 800×480 touch-oriented radar interface |
| `docs/` | Product definition, specifications, ADRs and plans |
| `config/` | Safe configuration examples |
| `hardware/`, `enclosure/` | Reference build and mechanical design |
| `scripts/`, `systemd/` | Development and appliance deployment |
| `tests/` | Automated contract and service checks |
| `release/` | Future image and release recipes |

Start with the [project definition](docs/PROJECT_DEFINITION.md), [architecture](docs/01_Architecture.md), and [roadmap](docs/03_Roadmap.md).

## Contributing

Contributions are very welcome, whether that is a reproducible bug report,
documentation improvement, hardware result, design suggestion, or focused code
change. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull
request. For sensitive security reports, follow [SECURITY.md](SECURITY.md).

## Appliance networking

On the Raspberry Pi appliance, **Map options → Wi-Fi network** scans NetworkManager and lets the user select a visible SSID; hidden SSIDs are intentionally not entered by hand. The installer grants the dedicated `piradar` service account only the NetworkManager permissions needed to scan and connect. `nmcli` must be installed for this control to be available.

## Licence

PiRadar is available under the [MIT License](LICENSE).
