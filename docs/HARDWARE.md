# Reference Hardware

## Proven reference appliance

- Raspberry Pi 3 Model B v1.2
- Debian 13 (Trixie), 64-bit
- 5-inch 800×480 HDMI display
- XPT2046/ADS7846-compatible resistive touch controller
- Chromium 150 on Wayland

The display PCB is marked “5inch HDMI Display”, 800×480, “XPT2046 Touch
Controller”, Rev3.0. No manufacturer name is printed. Its resistive panel works
with a fingertip or a passive stylus; a stylus is useful for precise selection
and does not need electronics, pairing, or charging.

The reference touch controller uses SPI0 chip-select 1 and GPIO 25 for PENIRQ. Debian's built-in `ads7846` overlay is enabled in `/boot/firmware/config.txt`:

```ini
dtparam=spi=on
dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,pmax=255,xohms=150
dtparam=xmin=200,xmax=3900,ymin=390,ymax=3910
```

Keep the calibration parameters on the continuation line. Raspberry Pi boot
configuration entries are limited to 98 characters; a single combined line is
silently truncated before the Y-axis values and leaves vertical touch input
misaligned.

The kernel exposes it as `ADS7846 Touchscreen`. Back up the existing boot
configuration before changing calibration values so the device can be restored
without relying on repository files.

The VC4 HDMI CEC receiver also advertises relative pointer axes despite there
being no mouse. Cage otherwise creates a stationary compositor cursor that CSS
cannot remove. `udev/99-piradar-input.rules` sets `LIBINPUT_IGNORE_DEVICE=1`
only for the `vc4-hdmi` input node; it does not disable HDMI video or touch.

## Open hardware work

Power measurements and enclosure dimensions remain to be recorded for a
reproducible build. Local ADS-B reception later requires a compatible RTL-SDR,
1090 MHz antenna, suitable placement, and a `readsb` provider integration.
