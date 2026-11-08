#!/usr/bin/env sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer as root." >&2
  exit 1
fi

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
install_dir=/opt/piradar
config_dir=/etc/piradar

if ! id piradar >/dev/null 2>&1; then
  useradd --system --home-dir "$install_dir" --shell /usr/sbin/nologin piradar
fi

install -d -m 0755 "$install_dir"
if [ "$source_dir" != "$install_dir" ]; then
  cp -R "$source_dir/backend" "$source_dir/frontend" "$source_dir/scripts" "$source_dir/boot" "$install_dir/"
fi
chmod 0755 "$install_dir/scripts/run-dev.sh" "$install_dir/scripts/start-kiosk.sh" "$install_dir/scripts/update.sh" "$install_dir/scripts/install-splash.sh"
install -d -m 0755 "$config_dir"
if [ ! -e "$config_dir/piradar.json" ]; then
  install -m 0644 "$source_dir/config/piradar.example.json" "$config_dir/piradar.json"
fi
install -m 0644 "$source_dir/systemd/piradar.service" /etc/systemd/system/piradar.service
install -m 0644 "$source_dir/systemd/cage@.service" /etc/systemd/system/cage@.service
install -m 0644 "$source_dir/udev/99-piradar-input.rules" /etc/udev/rules.d/99-piradar-input.rules
install -d -m 0755 /etc/polkit-1/rules.d
install -m 0644 "$source_dir/polkit/50-piradar-network.rules" /etc/polkit-1/rules.d/50-piradar-network.rules
install -m 0644 "$source_dir/polkit/50-piradar-power.rules" /etc/polkit-1/rules.d/50-piradar-power.rules
udevadm control --reload-rules
systemctl daemon-reload

if ! command -v nmcli >/dev/null 2>&1; then
  echo "Warning: nmcli is not installed; the in-app Wi-Fi picker will be unavailable." >&2
fi

echo "PiRadar installed. Review $config_dir/piradar.json, then run:"
echo "  systemctl enable --now piradar cage@tty1"
