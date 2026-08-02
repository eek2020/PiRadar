# Maintenance Guide

## Routine operation

Inspect application logs with `journalctl -u piradar`. Configuration lives outside the checkout so source upgrades do not replace local settings.

## Updating

Updates should install from a tagged release, run automated checks and restart the service. Keep the previous working release or SD image available for rollback until the new version passes a smoke test.

## Fault isolation

1. Check `systemctl status piradar`.
2. Request `http://127.0.0.1:8080/api/health` locally.
3. Distinguish service failure from provider or network failure.
4. Review recent journal entries without publishing tokens or exact private coordinates.
5. Reproduce against the mock provider before changing UI code.

