# Cleanup Plan

Before release:

- Remove temporary prototype HTML and launch commands from the Pi
- Consolidate configuration under `/etc/piradar`
- Remove unused packages and scripts
- Validate autostart, recovery and clean shutdown
- Verify no secrets or API tokens are present in the image
- Back up and checksum the release SD image

