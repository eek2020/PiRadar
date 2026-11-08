# Maintenance Guide

## Routine operation

Inspect application logs with `journalctl -u piradar`. Configuration lives in `/etc/piradar`; persistent enrichment and optional API credentials live in `/var/lib/piradar`. Both locations sit outside the checkout so source upgrades do not replace local settings. Never copy `credentials.json` into the repository or attach it to diagnostics.

## Updating over the air

PiRadar updates itself from GitHub. Nothing needs to be connected to it.

- **Map options → Software update** shows the installed commit and the channel it follows, checks GitHub for the newest commit, and offers **Install update** when there is a genuinely newer version.
- **Update automatically** is **on by default**. `piradar-update.timer` checks GitHub every 15 minutes and installs any newer commit on the channel, so a Pi anywhere, behind any router, updates itself soon after a push with nobody at it. If an update needs a restart (for example a boot setting), the Pi restarts itself, at most once per version. Checks that find nothing are silent; switch it off on the screen if wanted.

Every update, however it starts, runs `scripts/update.sh` as root under systemd. It resolves the channel to an exact commit, downloads it and runs the test suite before changing anything. Then it backs up `/opt/piradar` to `/opt/piradar.previous`, installs, restarts and checks `/api/health`. If the install or the health check fails, it restores the backup automatically. Automatic and touchscreen updates never move to an older commit: if the channel is behind what is installed, they do nothing.

The app itself never gets root. It can only start `piradar-update.service`, which `polkit/50-piradar-update.rules` allows for the `piradar` user and nothing else, and it can write the automatic-update switch to `/var/lib/piradar/update-settings.json`. Progress is reported in `/var/lib/piradar-update/status.json` and the installed version in `/opt/piradar/VERSION.json`.

**Channels.** The Pi follows the branch or tag it was last updated to by hand, stored in `/etc/piradar/update-channel` (default `main`). To change it, or to deliberately go back to an older version, run the updater by hand once:

```bash
ssh -t pi@planeradar.local sudo /opt/piradar/scripts/update.sh main        # follow main from now on
ssh -t pi@planeradar.local sudo /opt/piradar/scripts/update.sh --rollback  # undo the last update
```

Settings in `/etc/piradar` and `/var/lib/piradar` are never touched by updates.

## Power

Map options → Power offers Shut down and Restart, each behind a confirm step. The service asks systemd-logind to act, and `polkit/50-piradar-power.rules` permits only those actions for the `piradar` user. The endpoint refuses requests that do not come from the Pi itself. After a shut down, wait for the green activity light to stop flashing before unplugging.

## Wi-Fi troubleshooting

When a connection fails, the Wi-Fi panel explains why under the password box and shows NetworkManager's own reason in small print. The same reason is written to the journal (`journalctl -u piradar | grep Wi-Fi`).

- **Network not in the list.** The Pi 3B only has 2.4GHz Wi-Fi. A router that broadcasts only on 5GHz will not appear; most routers can enable 2.4GHz, or offer a 2.4GHz guest network.
- **"Wi-Fi passwords are 8 to 63 characters long".** The password typed cannot be valid. Use the eye button to check it.
- **Right password, still refused, router shows "WPA2 WPA3".** This is a known problem with the Pi 3's Broadcom Wi-Fi and routers in WPA2/WPA3 mixed (transition) mode ([raspberrypi/linux#4976](https://github.com/raspberrypi/linux/issues/4976)). Wi-Fi compatibility mode, which makes the Pi join over WPA2, fixes it. It is **on by default** for Pi 3 and Zero 2 boards: every install and over-the-air update switches it on, and the update asks for a restart to finish. If someone turns it off, that choice is remembered and updates leave it off. To manage it by hand:

  ```bash
  sudo /opt/piradar/scripts/wifi-compat.sh on       # then restart the Pi
  sudo /opt/piradar/scripts/wifi-compat.sh status
  sudo /opt/piradar/scripts/wifi-compat.sh off      # undo, then restart
  ```

  A WPA3-only network will still not work on this hardware; switch the router to WPA2/WPA3 mixed mode or use a WPA2 guest network.
- **"Did not give it an address".** PiRadar joined but the router refused it an IP address. Restart the router, or check MAC filtering or a device limit.

## Boot splash (optional)

`scripts/install-splash.sh` replaces the Raspberry Pi boot, restart and shutdown screens with the PiRadar radar splash. It installs the `piradar` Plymouth theme, adds `disable_splash=1` to `config.txt` and `logo.nologo vt.global_cursor_default=0` to `cmdline.txt`, and makes the kiosk keep the splash on screen until the app draws. Both boot files are backed up to `*.piradar-bak` first.

```bash
sudo /opt/piradar/scripts/install-splash.sh            # install, or refresh after an update
sudo /opt/piradar/scripts/install-splash.sh --remove   # restore the original screens
```

The artwork is generated by `scripts/build-splash.py` (needs Pillow, run on a development machine) and committed, so the Pi never needs it. Installing the splash is a one-off, opt-in step. After that, `update.sh` keeps it current: when an update changes the theme it re-runs the splash installer (rebuilding the initramfs only then), and a splash failure is reported as a warning without failing the update.

## Fault isolation

1. Check `systemctl status piradar`.
2. Request `http://127.0.0.1:8080/api/health` locally.
3. Distinguish service failure from provider or network failure.
4. Review recent journal entries without publishing tokens or exact private coordinates.
5. Reproduce against the mock provider before changing UI code.

## Data-service credentials

Credentials can be saved or cleared under Map options → Data services. The UI intentionally cannot reveal an existing value (the eye button only shows what is currently typed in the box); replace it by entering a new complete credential set. Saving credentials prepares future connectors but does not enable them or make paid calls. Back up the protected state directory only when credential recovery is genuinely required, and preserve its owner-only permissions.
