#!/usr/bin/env sh
# ---------------------------------------------------------------------------
# PiRadar boot splash installer (optional)
#
# Replaces the Raspberry Pi boot, restart and shutdown screens with the
# PiRadar radar splash:
#   - installs the "piradar" Plymouth theme and rebuilds the initramfs
#   - config.txt: disable_splash=1          (no rainbow square at power-on)
#   - cmdline.txt: logo.nologo, hidden cursor, keeps "quiet splash"
#   - kiosk: asks Plymouth to leave its last frame on screen until the
#     radar app draws, so there is no flash of console text in between
#
# Boot files are backed up to *.piradar-bak before the first change. Only the
# options this script added are removed again, so other PiRadar boot settings
# (such as Wi-Fi compatibility mode) are left alone.
#
# Usage:
#   sudo /opt/piradar/scripts/install-splash.sh            # install / refresh
#   sudo /opt/piradar/scripts/install-splash.sh --remove   # put everything back
#
# Takes a minute or two on a Pi 3, mostly rebuilding the initramfs.
# ---------------------------------------------------------------------------
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this with sudo." >&2
  exit 1
fi

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
theme_source="$source_dir/boot/plymouth/piradar"
theme_dir=/usr/share/plymouth/themes/piradar
state_file=/etc/piradar/splash-previous-theme
dropin_dir=/etc/systemd/system/cage@tty1.service.d
dropin_file="$dropin_dir/piradar-splash.conf"

added_file=/etc/piradar/splash-cmdline-added

# Shared boot-file helpers (boot_dir, cmdline, config, cmdline_add, ...).
. "$source_dir/scripts/lib/bootline.sh"

for tool in plymouth-set-default-theme update-initramfs; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "$tool is missing. Install Plymouth first: sudo apt install plymouth" >&2
    exit 1
  fi
done
if [ ! -f "$cmdline" ] || [ ! -f "$config" ]; then
  echo "Could not find cmdline.txt and config.txt in $boot_dir." >&2
  exit 1
fi

# --- Remove ----------------------------------------------------------------
if [ "${1:-}" = "--remove" ]; then
  # Remove only the kernel options this script added. Older installs did not
  # record them, so fall back to the two options it always adds itself.
  if [ -s "$added_file" ]; then
    # shellcheck disable=SC2046
    cmdline_remove $(cat "$added_file")
  else
    cmdline_remove logo.nologo vt.global_cursor_default=0
  fi
  rm -f "$added_file"
  # Remove the block it appended to config.txt, and nothing else.
  python3 - "$config" <<'PY2'
import os, sys
path = sys.argv[1]
text = open(path).read()
block = "\n[all]\n# PiRadar boot splash\ndisable_splash=1\n"
if block in text:
    temporary = path + ".piradar-new"
    with open(temporary, "w") as stream:
        stream.write(text.replace(block, "", 1))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
PY2
  rm -f "$dropin_file"
  rmdir "$dropin_dir" 2>/dev/null || true
  systemctl daemon-reload
  previous=$(cat "$state_file" 2>/dev/null || true)
  if [ -n "$previous" ] && [ "$previous" != "piradar" ]; then
    plymouth-set-default-theme "$previous"
  else
    plymouth-set-default-theme --reset
  fi
  rm -rf "$theme_dir" "$state_file"
  echo "Rebuilding the initramfs…"
  update-initramfs -u >/dev/null
  echo "PiRadar splash removed. It will be gone after the next restart."
  exit 0
fi

# --- Install ---------------------------------------------------------------
if [ ! -f "$theme_source/piradar.plymouth" ]; then
  echo "Theme files not found in $theme_source. Update PiRadar first." >&2
  exit 1
fi

# 1. Theme files. Remember the current theme once, for --remove.
current=$(plymouth-set-default-theme 2>/dev/null || true)
if [ ! -e "$state_file" ] && [ "$current" != "piradar" ]; then
  install -d -m 0755 "$(dirname "$state_file")"
  printf '%s\n' "$current" >"$state_file"
fi
install -d -m 0755 "$theme_dir"
install -m 0644 "$theme_source"/* "$theme_dir/"

# 2. config.txt: hide the rainbow square. Added in its own [all] section so it
#    applies whatever section the file happens to end in.
if ! grep -q '^disable_splash=1' "$config"; then
  backup_once "$config"
  { cat "$config"; printf '\n[all]\n# PiRadar boot splash\ndisable_splash=1\n'; } | replace_file "$config"
fi

# 3. cmdline.txt: must stay a single line. Add any missing options to it.
# Record what was actually added, so --remove takes out exactly those.
install -d -m 0755 "$(dirname "$added_file")"
cmdline_add quiet splash logo.nologo vt.global_cursor_default=0 >>"$added_file"

# 4. Kiosk hand-over: keep the splash's last frame on screen until the app
#    paints. The leading "-" means a missing Plymouth never blocks the kiosk.
install -d -m 0755 "$dropin_dir"
cat >"$dropin_file" <<'EOF'
# Installed by PiRadar install-splash.sh
[Service]
ExecStartPre=-/usr/bin/plymouth quit --retain-splash
EOF
systemctl daemon-reload

# 5. Make it the default theme and rebuild the initramfs, which is where the
#    boot-time copy of the theme lives.
plymouth-set-default-theme piradar
echo "Rebuilding the initramfs (a minute or two on a Pi 3)…"
update-initramfs -u >/dev/null

echo "PiRadar splash installed. You will see it from the next restart."
echo "Undo with: sudo $source_dir/scripts/install-splash.sh --remove"
