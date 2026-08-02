# Maintenance Guide

## Routine operation

Inspect application logs with `journalctl -u piradar`. Configuration lives in `/etc/piradar`; persistent enrichment and optional API credentials live in `/var/lib/piradar`. Both locations sit outside the checkout so source upgrades do not replace local settings. Never copy `credentials.json` into the repository or attach it to diagnostics.

## Updating

Updates should install from a tagged release, run automated checks and restart the service. Keep the previous working release or SD image available for rollback until the new version passes a smoke test.

## Fault isolation

1. Check `systemctl status piradar`.
2. Request `http://127.0.0.1:8080/api/health` locally.
3. Distinguish service failure from provider or network failure.
4. Review recent journal entries without publishing tokens or exact private coordinates.
5. Reproduce against the mock provider before changing UI code.

## Data-service credentials

Credentials can be saved or cleared under Map options → Data services. The UI intentionally cannot reveal an existing value; replace it by entering a new complete credential set. Saving credentials prepares future connectors but does not enable them or make paid calls. Back up the protected state directory only when credential recovery is genuinely required, and preserve its owner-only permissions.
