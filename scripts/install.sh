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

python3 -m venv "$install_dir/.venv"
"$install_dir/.venv/bin/pip" install --no-build-isolation "$source_dir"
install -d -m 0755 "$install_dir/frontend"
cp -R "$source_dir/frontend/." "$install_dir/frontend/"
install -d -m 0755 "$config_dir"
if [ ! -e "$config_dir/piradar.json" ]; then
  install -m 0644 "$source_dir/config/piradar.example.json" "$config_dir/piradar.json"
fi
install -m 0644 "$source_dir/systemd/piradar.service" /etc/systemd/system/piradar.service
systemctl daemon-reload

echo "PiRadar installed. Review $config_dir/piradar.json, then run:"
echo "  systemctl enable --now piradar"
