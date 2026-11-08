# Maintenance Guide

## Routine operation

Inspect application logs with `journalctl -u piradar`. Configuration lives in `/etc/piradar`; persistent enrichment and optional API credentials live in `/var/lib/piradar`. Both locations sit outside the checkout so source upgrades do not replace local settings. Never copy `credentials.json` into the repository or attach it to diagnostics.

## Updating over the air

`scripts/update.sh` updates a running Pi from GitHub. It downloads the requested branch, tag or commit, runs the test suite against the download, backs up `/opt/piradar` to `/opt/piradar.previous`, runs the installer and restarts the service. If `/api/health` does not answer within about 20 seconds, or the installer fails, it restores the backup automatically. Settings in `/etc/piradar` and `/var/lib/piradar` are never touched.

From another machine on the same network:

```bash
ssh -t pi@planeradar.local sudo /opt/piradar/scripts/update.sh            # latest main
ssh -t pi@planeradar.local sudo /opt/piradar/scripts/update.sh v0.2.0     # a tag
ssh -t pi@planeradar.local sudo /opt/piradar/scripts/update.sh --rollback # undo the last update
```

Prefer tagged releases for anything you are not actively testing. `/opt/piradar/VERSION` records what was installed and when.

## Power

Map options → Power offers Shut down and Restart, each behind a confirm step. The service asks systemd-logind to act, and `polkit/50-piradar-power.rules` permits only those actions for the `piradar` user. The endpoint refuses requests that do not come from the Pi itself. After a shut down, wait for the green activity light to stop flashing before unplugging.

## Fault isolation

1. Check `systemctl status piradar`.
2. Request `http://127.0.0.1:8080/api/health` locally.
3. Distinguish service failure from provider or network failure.
4. Review recent journal entries without publishing tokens or exact private coordinates.
5. Reproduce against the mock provider before changing UI code.

## Data-service credentials

Credentials can be saved or cleared under Map options → Data services. The UI intentionally cannot reveal an existing value (the eye button only shows what is currently typed in the box); replace it by entering a new complete credential set. Saving credentials prepares future connectors but does not enable them or make paid calls. Back up the protected state directory only when credential recovery is genuinely required, and preserve its owner-only permissions.
