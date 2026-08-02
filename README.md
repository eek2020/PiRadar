# PiRadar

PiRadar is a dedicated Raspberry Pi aircraft-radar appliance designed to boot directly into a polished, full-screen airspace display.

The first release will use an online ADS-B data provider. Its architecture deliberately supports a later local 1090 MHz receiver using an RTL-SDR and `readsb`, without replacing the user interface.

> PiRadar is an informational display, not a complete or safety-critical source of aircraft information.

## Current status

The Raspberry Pi 3B, Debian 13, 800×480 HDMI display and Chromium/Wayland kiosk approach have been proven in a disposable prototype. This repository is the clean implementation source of truth and currently contains the first runnable mock-data vertical slice.

## Try it

PiRadar requires Python 3.11 or newer and has no runtime dependencies at this stage.

```bash
./scripts/run-dev.sh
```

Open [http://localhost:8080](http://localhost:8080). Configure another location or range by copying `config/piradar.example.json` to the ignored `config/piradar.json`, editing it, and running:

```bash
PIRADAR_CONFIG=config/piradar.json ./scripts/run-dev.sh
```

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

Start with the [project definition](docs/PROJECT_DEFINITION.md), [architecture](docs/01_Architecture.md), and [roadmap](docs/03_Roadmap.md). Contributions are welcome through focused issues and pull requests; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

PiRadar is available under the [MIT License](LICENSE).
