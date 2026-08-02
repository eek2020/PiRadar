# Architecture

```text
Power on
  ↓
Linux boot and splash
  ↓
piradar.service
  ↓
Python HTTP service ──→ aircraft provider
  ↓                         ├── mock (development)
Static radar UI             ├── online ADS-B (phase 3)
                            └── readsb (future)
```

## Components

- `backend/piradar`: dependency-light Python HTTP service and data abstraction
- `frontend`: touch-oriented HTML, CSS and JavaScript radar interface
- `config`: deploy-time settings examples
- `systemd`: appliance service definition
- `scripts`: development and installation helpers
- `tests`: backend contract and provider tests

The UI consumes only the internal `/api/aircraft` contract. Changing from online data to a local receiver therefore does not require replacing the frontend.

On the reference appliance, `piradar.service` runs the local application and `cage@tty1.service` owns the display session. Cage launches Chromium through `scripts/start-kiosk.sh` only after the health endpoint responds.

## API surface

- `GET /api/health` — process and provider health
- `GET /api/config` — public display settings
- `GET /api/aircraft` — normalized aircraft snapshot
- `GET /` — radar frontend
