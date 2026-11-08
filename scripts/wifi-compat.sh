#!/usr/bin/env sh
# ---------------------------------------------------------------------------
# Wi-Fi compatibility mode for Pi 3 class boards
#
# The Broadcom Wi-Fi in the Pi 3 / 3A+ / Zero 2 W (brcmfmac driver) often
# fails to join routers running WPA2/WPA3 "mixed" or "transition" mode, even
# with the right password, while other devices connect fine. Many current
# UK ISP routers ship in that mode.
#
# The widely confirmed fix is to stop the Wi-Fi firmware doing the WPA3 (SAE)
# and key handshake itself, so the Pi joins the router over plain WPA2:
#     brcmfmac.feature_disable=0x82000
# See https://github.com/raspberrypi/linux/issues/4976
#
# Networks that are WPA3-only still will not work on this hardware; the
# router needs WPA2 or WPA2/WPA3 mixed mode (or a WPA2 guest network).
#
# Usage:
#   sudo /opt/piradar/scripts/wifi-compat.sh status
#   sudo /opt/piradar/scripts/wifi-compat.sh on     # then restart the Pi
#   sudo /opt/piradar/scripts/wifi-compat.sh off    # then restart the Pi
# ---------------------------------------------------------------------------
set -eu

option="brcmfmac.feature_disable=0x82000"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this with sudo." >&2
  exit 1
fi

# Shared boot-file helpers (boot_dir, cmdline_add, cmdline_remove, ...).
. "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/lib/bootline.sh"

if [ ! -f "$cmdline" ]; then
  echo "Could not find cmdline.txt in $boot_dir." >&2
  exit 1
fi

# Is the option active right now (as opposed to waiting for a restart)?
running_with_option() {
  case " $(cat /proc/cmdline 2>/dev/null) " in
    *" $option "*) return 0 ;;
    *) return 1 ;;
  esac
}

case "${1:-status}" in
  on)
    if cmdline_has "$option"; then
      echo "Wi-Fi compatibility mode is already on."
    else
      cmdline_add "$option" >/dev/null
      echo "Wi-Fi compatibility mode is on. Restart the Pi for it to take effect."
    fi
    ;;
  off)
    if cmdline_has "$option"; then
      cmdline_remove "$option"
      echo "Wi-Fi compatibility mode is off. Restart the Pi for it to take effect."
    else
      echo "Wi-Fi compatibility mode is already off."
    fi
    ;;
  status)
    if cmdline_has "$option"; then saved=on; else saved=off; fi
    if running_with_option; then active=on; else active=off; fi
    echo "Wi-Fi compatibility mode: $saved (currently running: $active)"
    [ "$saved" = "$active" ] || echo "Restart the Pi to apply the change."
    ;;
  *)
    echo "Usage: $0 on|off|status" >&2
    exit 1
    ;;
esac
