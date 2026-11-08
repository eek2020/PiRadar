#!/usr/bin/env python3
"""Render the PiRadar Plymouth boot splash artwork.

Produces everything the theme in ``boot/plymouth/piradar`` needs:

  sweep-00.png .. sweep-35.png   radar scope, sweep rotated 10 degrees per frame
  wordmark.png                    "PiRadar" wordmark
  status-boot.png etc.            status lines for boot / restart / shut down

All text is pre-rendered so the Pi needs no fonts or extra Plymouth plugins
inside the initramfs. Requires Pillow, run on a development machine:

    python3 scripts/build-splash.py

The PNGs are committed, so the Pi itself never runs this script.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parents[1] / "boot" / "plymouth" / "piradar"

# Palette from frontend/styles.css so the splash matches the app.
BACKGROUND = (7, 16, 20)          # theme-color #071014
MINT = (125, 255, 213)            # --mint
MINT_DIM = (60, 167, 139)         # --mint-dim
MUTED = (120, 145, 143)           # --muted
LINE = (35, 65, 62)               # --line

SCOPE = 220                       # finished scope size in pixels
SS = 3                            # supersampling factor for smooth edges
FRAMES = 36                       # 10 degrees per frame
SWEEP_TRAIL = 70                  # degrees of fading trail behind the beam

# A few fixed "aircraft" as (bearing degrees, distance 0..1). Each one lights
# up as the beam passes over it, then fades, like a real scope.
BLIPS = [(38, 0.62), (127, 0.34), (211, 0.78), (296, 0.51), (338, 0.22)]

FONT_DIR = Path("/usr/share/fonts/opentype/inter")


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    for name in (f"Inter-{weight}.otf", f"InterDisplay-{weight}.otf"):
        path = FONT_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.truetype("DejaVuSans.ttf", size)


def mix(colour: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    """Blend a colour towards the background; amount 1 = full colour."""
    return tuple(round(b + (c - b) * amount) for c, b in zip(colour, BACKGROUND))


def scope_frame(angle: float) -> Image.Image:
    size = SCOPE * SS
    centre = size / 2
    radius = size / 2 - 3 * SS
    image = Image.new("RGB", (size, size), BACKGROUND)
    draw = ImageDraw.Draw(image)

    # Sweep trail: thin wedges whose brightness falls off behind the beam.
    # Bearings are clockwise from north; Pillow angles are clockwise from east.
    for step in range(SWEEP_TRAIL):
        strength = (1 - step / SWEEP_TRAIL) ** 2 * 0.28
        start = angle - step - 1 - 90
        draw.pieslice(
            (centre - radius, centre - radius, centre + radius, centre + radius),
            start, start + 1.2, fill=mix(MINT, strength),
        )

    # Range rings and crosshair.
    for fraction in (1.0, 0.66, 0.33):
        r = radius * fraction
        draw.ellipse((centre - r, centre - r, centre + r, centre + r),
                     outline=LINE if fraction < 1 else MINT_DIM, width=SS * (2 if fraction == 1 else 1))
    draw.line((centre, centre - radius, centre, centre + radius), fill=LINE, width=SS)
    draw.line((centre - radius, centre, centre + radius, centre), fill=LINE, width=SS)

    # Blips brighten when the beam has just passed them.
    for bearing, distance in BLIPS:
        since = (angle - bearing) % 360
        glow = max(0.0, 1 - since / 240)
        if glow <= 0:
            continue
        rad = math.radians(bearing - 90)
        x = centre + math.cos(rad) * radius * distance
        y = centre + math.sin(rad) * radius * distance
        dot = 3.2 * SS
        draw.ellipse((x - dot, y - dot, x + dot, y + dot), fill=mix(MINT, 0.25 + 0.75 * glow))

    # The beam itself.
    rad = math.radians(angle - 90)
    draw.line((centre, centre, centre + math.cos(rad) * radius, centre + math.sin(rad) * radius),
              fill=MINT, width=2 * SS)
    draw.ellipse((centre - 3 * SS, centre - 3 * SS, centre + 3 * SS, centre + 3 * SS), fill=MINT)

    # Soft outer glow on the rim, then scale down for anti-aliasing.
    image = image.resize((SCOPE, SCOPE), Image.LANCZOS)
    return image


def text_image(text: str, typeface: ImageFont.FreeTypeFont, colour, tracking: int = 0) -> Image.Image:
    """Render text on the splash background, cropped to a tidy box."""
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    widths = [probe.textlength(ch, font=typeface) for ch in text]
    width = int(sum(widths) + tracking * (len(text) - 1)) + 8
    ascent, descent = typeface.getmetrics()
    image = Image.new("RGB", (width, ascent + descent + 6), BACKGROUND)
    draw = ImageDraw.Draw(image)
    x = 4.0
    for ch, w in zip(text, widths):
        draw.text((x, 3), ch, font=typeface, fill=colour)
        x += w + tracking
    return image


def status_image(title: str, detail: str) -> Image.Image:
    heading = text_image(title.upper(), font("Medium", 15), MINT, tracking=2)
    if not detail:
        return heading
    body = text_image(detail, font("Regular", 13), MUTED)
    width = max(heading.width, body.width)
    image = Image.new("RGB", (width, heading.height + body.height + 4), BACKGROUND)
    image.paste(heading, ((width - heading.width) // 2, 0))
    image.paste(body, ((width - body.width) // 2, heading.height + 4))
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for index in range(FRAMES):
        scope_frame(index * 360 / FRAMES).save(OUT / f"sweep-{index:02d}.png", optimize=True)

    wordmark = text_image("PiRadar", font("SemiBold", 30), MINT, tracking=1)
    wordmark.save(OUT / "wordmark.png", optimize=True)

    statuses = {
        "boot": ("Starting", ""),
        "reboot": ("Restarting", "The radar will be back in about a minute"),
        "shutdown": ("Shutting down", "Unplug once the green light on the Pi stops flashing"),
        "updates": ("Updating", "Please leave PiRadar switched on"),
    }
    for mode, (title, detail) in statuses.items():
        status_image(title, detail).save(OUT / f"status-{mode}.png", optimize=True)

    # A full-size preview, for checking the layout without a Pi.
    preview = Image.new("RGB", (800, 480), BACKGROUND)
    preview.paste(Image.open(OUT / "sweep-09.png"), ((800 - SCOPE) // 2, 62))
    preview.paste(wordmark, ((800 - wordmark.width) // 2, 300))
    status = Image.open(OUT / "status-shutdown.png")
    preview.paste(status, ((800 - status.width) // 2, 352))
    preview.save(OUT.parent / "preview.png")
    print(f"Wrote {FRAMES} sweep frames, wordmark and status images to {OUT}")


if __name__ == "__main__":
    main()
