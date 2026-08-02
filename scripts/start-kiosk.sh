#!/usr/bin/env sh
set -eu

url=${PIRADAR_URL:-http://127.0.0.1:8080}
profile_dir=${PIRADAR_CHROMIUM_PROFILE:-/home/pi/.config/piradar-browser}

for attempt in $(seq 1 40); do
  if /usr/bin/python3 -c \
    "import urllib.request; urllib.request.urlopen('$url/api/health', timeout=0.5)" \
    >/dev/null 2>&1
  then
    break
  fi
  if [ "$attempt" -eq 40 ]; then
    echo "PiRadar did not become ready at $url" >&2
    exit 1
  fi
  sleep 0.25
done

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
