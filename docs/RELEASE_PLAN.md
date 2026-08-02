# Release Plan

## Release stages

1. **Developer preview:** mock provider and desktop workflow
2. **Hardware alpha:** repeatable installation and kiosk startup on the reference Pi
3. **Provider beta:** live ADS-B source, offline behaviour and usage-policy review
4. **Release candidate:** clean-image build, soak test and documentation audit
5. **v1.0:** tagged source, checksums, installation guide and known limitations

## Release gate

A release requires passing CI, a clean install on reference hardware, an 800×480 UI review, recovery tests and an updated changelog. Generated images or archives must include checksums and must never contain credentials or the maintainer's private location.

