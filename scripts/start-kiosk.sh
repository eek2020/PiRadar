#!/usr/bin/env sh
set -eu

url=${PIRADAR_URL:-http://127.0.0.1:8080}
profile_dir=${PIRADAR_CHROMIUM_PROFILE:-/home/pi/.config/piradar-browser}

exec /usr/bin/chromium \
  --ozone-platform=wayland \
  --kiosk \
  --force-dark-mode \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --password-store=basic \
  --user-data-dir="$profile_dir" \
  --disable-session-crashed-bubble \
  --disable-background-networking \
  --disable-component-update \
  --disable-default-apps \
  --disable-extensions \
  --disable-sync \
  --disable-features=TranslateUI \
  "$url"

