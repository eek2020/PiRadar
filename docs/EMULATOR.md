# PiRadar emulator

Rehearse a change on an emulated Pi before it is pushed, and so before it reaches a real PiRadar over the air.

```bash
./emulate                         # the neighbour scenario (default)
./emulate --scenario wpa3-mixed   # pick a scenario
./emulate --list                  # list scenarios
```

It opens a page in your browser. On the left is the **real PiRadar interface** at 800×480, served by the real backend from this checkout; click it as you would tap the touchscreen. On the right is the control panel: the router scenario, the emulated Pi's state, actions, and its system log. Every emulated Wi-Fi network uses the password `radar-test-1`. Stop it with Ctrl+C; all emulated state lives in a temporary folder that is deleted on exit.

Needs Python 3.11 or newer. macOS's built-in `python3` is often older; `./emulate` looks for `python3.13`, `python3.12` and `python3.11` first, and tells you how to install one if none is found. Nothing else needs installing. Map tiles load from OpenStreetMap, so the screen needs an internet connection; aircraft are mock data.

## What is real and what is emulated

| Real (from this checkout) | Emulated (`emulator/device.py`) |
| --- | --- |
| Backend, API, frontend, Wi-Fi/power/update adapters, error advice, Details screen | NetworkManager (`nmcli`), the system log (`journalctl`), `systemctl` restarts and power, boot files, the router |

The emulator answers the exact commands PiRadar's adapters run, in NetworkManager's real output formats, so PiRadar's own parsing and logic are exercised. It also reproduces NetworkManager behaviour that has caught us out: a failed attempt leaves its profile saved, and a saved profile with a wrong key keeps failing with "Secrets were required, but not provided" even when the right password is typed. Boot settings work as on a Pi: the boot line on disk only takes effect after a restart.

What it cannot do is reproduce a specific router's firmware or the Broadcom Wi-Fi chip itself. Scenarios encode the *behaviour* we know about; log lines are representative, not copies. A fault nobody has characterised yet will not appear here; use the Wi-Fi **Details** screen on the real Pi to find it, then add a scenario for it.

## Scenarios

| Name | Router behaviour |
| --- | --- |
| `neighbour` | WPA2. Earlier failed attempts left a saved profile with a wrong key; current PiRadar clears it and connects. |
| `home` | Normal WPA2, plus an open guest network. |
| `wpa3-mixed` | WPA2/WPA3 mixed mode: a Pi 3 fails with the right password until Wi-Fi compatibility mode is on *and* the Pi has restarted. |
| `wpa3-only` | WPA3 only: a Pi 3 can never join. |
| `weak-signal` | Attempts time out. |
| `no-dhcp` | Password accepted, no IP address given. |

Scenarios live in `emulator/scenarios.py`; a new one is a network list plus a rule deciding the outcome of each attempt.

## Control panel actions

- **Restart Pi** and **Power on**: what `systemctl reboot` and a power cycle do; the screen reloads like the kiosk.
- **Compat mode on / off**: change the boot line on disk, as an update or `scripts/wifi-compat.sh` would. Shown as "saved, needs a restart" until you restart.
- **Forget saved Wi-Fi**: remove saved Wi-Fi profiles.
- **Publish an update**: pretend a new commit was pushed. Software update on the screen then offers it, and installing walks through the real updater's stages (and restarts the Pi itself if a boot setting is waiting).

## Tests

`tests/test_emulator.py` runs PiRadar's real Wi-Fi code against every scenario, so the scenarios double as regression tests. They run with the rest of the suite, including on the Pi before every over-the-air update.
