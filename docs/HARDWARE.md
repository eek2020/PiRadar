# Reference Hardware

## Proven prototype

- Raspberry Pi 3 Model B v1.2
- Debian 13 (Trixie), 64-bit
- 5-inch 800×480 HDMI display
- XPT2046/ADS7846-compatible resistive touch controller
- Chromium 150 on Wayland

The prototype touch controller uses SPI0 chip-select 1 and GPIO 25 for PENIRQ. Debian's built-in `ads7846` overlay is enabled in `/boot/firmware/config.txt`:

```ini
dtparam=spi=on
dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900
```

The kernel exposes it as `ADS7846 Touchscreen`. The prototype's pre-change boot configuration is preserved at `/boot/firmware/config.txt.piradar-before-touch-20260802`.

## Open hardware work

The display board is marked “5inch HDMI Display”, 800×480, XPT2046 Touch Controller, Rev3.0. Its manufacturer is not printed. Power budget and enclosure dimensions remain to be recorded before the first hardware alpha. Local ADS-B reception later requires a compatible RTL-SDR, 1090 MHz antenna and suitable placement.
