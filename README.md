# PiRadar

PiRadar turns a Raspberry Pi and a compact touch display into a dedicated,
always-on map of the aircraft overhead. Power it on and it boots into a calm,
full-screen radar view—no desktop, browser controls, keyboard, or mouse needed.

Live nearby positions come from adsb.lol, while the interface adds aircraft
type, callsign, route, altitude, speed, heading, distance, airport context, and
a short trail. Touch an aircraft to find out what it is and where it is going;
pan the map to explore, or tap the home control to return to your saved location.

> PiRadar is an informational display, not a complete or safety-critical source
> of aircraft information. Never use it for navigation or separation.

## Project status

PiRadar is a **working hardware beta**. The current `main` branch has been run
and demonstrated end to end on the reference Raspberry Pi, including automatic
kiosk startup, live aircraft display, calibrated touch input, postcode
positioning, and changing Wi-Fi from the touchscreen.

The application and reference installation are working, but this is still an
enthusiast-built appliance rather than a packaged consumer product. A clean
image installer, long-duration soak testing, custom boot splash, and wider
hardware testing remain future work.

## What you can do

- Watch live aircraft move across a full-screen geographic map.
- Tap an aircraft for identity, route, altitude, speed, track, distance, squawk,
  and ICAO details when the source provides them.
- Filter traffic by aircraft class or altitude and show short movement trails.
- Show nearby UK airports and tap one for its name, codes, class, and distance.
- Switch between colour and dark maps, altitude colours and amber symbols, and
  optional callsign labels.
- Set a new radar centre with a UK postcode—useful when taking PiRadar to a new
  home or on a trip.
- Scan for and join a visible Wi-Fi network entirely on the touchscreen.
- Keep using the last aircraft snapshot when the live source briefly fails,
  with stale and offline states shown clearly.

## Proven reference hardware

The completed reference appliance uses:

- Raspberry Pi 3 Model B v1.2
- Debian 13 (Trixie), 64-bit
- A board marked **“5inch HDMI Display”**, 800×480,
  **“XPT2046 Touch Controller”**, **Rev3.0**
- Chromium 150 running under the Cage Wayland kiosk

The display manufacturer is not printed on the board. The XPT2046 is a
resistive touch controller compatible with the Linux ADS7846 driver, so Linux
reports the input as `ADS7846 Touchscreen`. It works with a fingertip or a
simple passive stylus; a stylus gives more precise control on the 5-inch panel.
It does not require an active or Bluetooth pen.

The reference wiring uses HDMI for video and SPI0 chip-select 1 plus GPIO 25 for
touch. Exact overlay, calibration, and false HDMI-pointer fixes are documented
in [Reference Hardware](docs/HARDWARE.md). Other HDMI displays may work, but
their touch wiring and calibration can differ.

## Using PiRadar

1. Power on the Pi and wait for the map. The status at the top changes from
   **Starting** to the current data state.
2. Tap an aircraft symbol to open its information card. Tap **×** to close it;
   the selected trail remains visible while the card is open.
3. Use **+**, **−**, and drag gestures to explore. Tap **⌖** to return to the
   saved radar centre.
4. Tap the filter button to choose aircraft types or altitude bands and to show
   or hide airports.
5. Tap **⚙ Map options** to change the display style, labels, radar postcode,
   or Wi-Fi network. Preferences are remembered on the appliance.
6. To move the appliance, open **Map options → Radar location**, enter the new
   UK postcode with the on-screen keyboard, and tap **Set**.
7. To change network, open **Map options → Wi-Fi network**, select a visible
   network, enter its password, and tap **Connect**. Hidden and enterprise Wi-Fi
   networks are intentionally not configured through this simple picker.

Map tiles, postcode lookup, and the current live-aircraft provider require an
internet connection. The mock provider remains available for demonstrations,
development, and fault isolation without live aircraft data.

## Installing on a Raspberry Pi

The current installer targets a prepared Debian/Raspberry Pi system with
Python 3.11+, Chromium, Cage, NetworkManager (`nmcli`), and a local `pi` kiosk
user. Clone the project to `/opt/piradar`, then run:

```bash
cd /opt/piradar
sudo ./scripts/install.sh
sudoedit /etc/piradar/piradar.json
sudo systemctl enable --now piradar cage@tty1
```

Set `"provider": "adsb_lol"` in `/etc/piradar/piradar.json` for live nearby
aircraft, or keep `"mock"` while testing. Review the complete
[build guide](docs/05_Build_Guide.md) and the display-specific
[hardware notes](docs/HARDWARE.md) before changing boot configuration.

The adsb.lol service is free and ODbL-licensed. Its operator asks production
users to make contact before relying on the service; PiRadar preserves its
attribution and is deliberately not presented as a safety tool.

## Try it on another computer

The development server uses only the Python standard library:

```bash
./scripts/run-dev.sh
```

Open [http://localhost:8080](http://localhost:8080). To use a local
configuration, copy `config/piradar.example.json` to the ignored
`config/piradar.json`, edit it, and run:

```bash
PIRADAR_CONFIG=config/piradar.json ./scripts/run-dev.sh
```

Run the test suite with:

```bash
PYTHONPATH=backend python3 -m unittest discover -s tests -v
```

## A future USB radio upgrade

PiRadar currently receives positions from an internet service. A valuable next
step is a compatible RTL-SDR USB dongle, a suitable 1090 MHz antenna, and
`readsb`. That would let the Pi receive ADS-B transmissions directly from
aircraft within radio range, reduce dependence on an online position source,
and turn the appliance into a genuinely local receiver.

The backend already isolates aircraft sources behind a provider interface, so
an RTL-SDR/`readsb` provider can be added without replacing the map or its touch
controls. This receiver path is planned, not implemented; antenna placement,
USB power, radio coverage, and regional radio rules will all matter.

## Enclosure

The reference unit has a physical case, but printable source files are not yet
part of the repository. An STL and preferably its editable source CAD may be
added after the board, connector, and mounting measurements are checked. It is
a welcome future addition, not a promised release dependency.

## Repository guide

| Path | Purpose |
|---|---|
| `backend/` | Python service, domain model and aircraft providers |
| `frontend/` | 800×480 touch-oriented radar interface |
| `docs/` | Build, hardware, product, architecture, and maintenance notes |
| `config/` | Safe configuration example |
| `hardware/`, `enclosure/` | Reference hardware and future mechanical files |
| `scripts/`, `systemd/` | Development and appliance deployment |
| `tests/` | Automated contract and service checks |
| `release/` | Future image and release recipes |

Start with the [build guide](docs/05_Build_Guide.md),
[reference hardware notes](docs/HARDWARE.md), and
[maintenance guide](docs/MAINTENANCE_GUIDE.md). Design and engineering context
lives in the [project definition](docs/PROJECT_DEFINITION.md),
[architecture](docs/01_Architecture.md), and [roadmap](docs/03_Roadmap.md).

## Contributing

Contributions are very welcome: reproducible bug reports, clearer instructions,
results from other Pi or display combinations, accessibility improvements,
case measurements, and focused code changes all help. Read
[CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. For sensitive
security reports, follow [SECURITY.md](SECURITY.md).

## Licence

PiRadar is available under the [MIT License](LICENSE).
