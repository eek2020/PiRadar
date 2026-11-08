#!/usr/bin/env sh
# ---------------------------------------------------------------------------
# PiRadar over-the-air updater
#
# Pulls a version of PiRadar from GitHub and installs it, with a safety net:
#   1. download the requested branch, tag or commit as a tarball
#   2. run the test suite against the download (nothing installed yet)
#   3. back up the current install to /opt/piradar.previous
#   4. run the normal installer, restart the service, check /api/health
#   5. if the health check fails, put the backup back automatically
#
# Usage (on the Pi, or from another machine over SSH):
#   sudo /opt/piradar/scripts/update.sh                 # latest main
#   sudo /opt/piradar/scripts/update.sh some-branch     # a branch
#   sudo /opt/piradar/scripts/update.sh v0.2.0          # a tag
#   sudo /opt/piradar/scripts/update.sh --rollback      # undo the last update
#   ssh -t pi@planeradar.local sudo /opt/piradar/scripts/update.sh
#
# Your settings in /etc/piradar and /var/lib/piradar are never touched.
# ---------------------------------------------------------------------------
set -eu

repo=${PIRADAR_REPO:-eek2020/PiRadar}
install_dir=/opt/piradar
backup_dir=/opt/piradar.previous
config_file=/etc/piradar/piradar.json

if [ "$(id -u)" -ne 0 ]; then
  echo "Run the updater with sudo." >&2
  exit 1
fi

# The installer overwrites this very file. Shells read scripts as they go, so
# run from a private copy to stop the update changing the script mid-run.
if [ -z "${PIRADAR_UPDATER_COPY:-}" ]; then
  self_copy=$(mktemp)
  cp "$0" "$self_copy"
  PIRADAR_UPDATER_COPY=$self_copy exec sh "$self_copy" "$@"
fi

# Health check URL: use the port from the Pi's config, defaulting to 8080.
port=$(python3 -c "import json,sys
try: print(int(json.load(open('$config_file')).get('port', 8080)))
except Exception: print(8080)" 2>/dev/null || echo 8080)
health_url="http://127.0.0.1:$port/api/health"

# Wait up to ~20 seconds for the backend to answer its health endpoint.
wait_for_health() {
  attempt=0
  while [ "$attempt" -lt 40 ]; do
    if curl -fsS --max-time 1 "$health_url" >/dev/null 2>&1; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 0.5
  done
  return 1
}

restart_services() {
  systemctl restart piradar
  if wait_for_health; then
    # Restart the kiosk too, so the screen loads the new frontend.
    systemctl restart cage@tty1 || true
    return 0
  fi
  return 1
}

restore_backup() {
  if [ ! -d "$backup_dir" ]; then
    echo "No previous version to roll back to." >&2
    return 1
  fi
  echo "Restoring previous version…"
  rm -rf "$install_dir.failed"
  mv "$install_dir" "$install_dir.failed"
  cp -a "$backup_dir" "$install_dir"
  restart_services
}

# --- Manual rollback -------------------------------------------------------
if [ "${1:-}" = "--rollback" ]; then
  rm -f "$PIRADAR_UPDATER_COPY"
  restore_backup
  echo "Rolled back to: $(cat "$install_dir/VERSION" 2>/dev/null || echo 'previous version')"
  exit 0
fi

ref=${1:-main}
work=$(mktemp -d)
trap 'rm -rf "$work" "$PIRADAR_UPDATER_COPY"' EXIT

# --- 1. Download -----------------------------------------------------------
echo "Downloading $repo at $ref…"
if ! curl -fsSL --retry 3 -o "$work/source.tgz" "https://github.com/$repo/archive/$ref.tar.gz"; then
  echo "Download failed. Check the branch or tag name, and that the Pi is online." >&2
  exit 1
fi
tar -xzf "$work/source.tgz" -C "$work"
source_dir=$(find "$work" -mindepth 1 -maxdepth 1 -type d | head -n 1)
if [ ! -f "$source_dir/scripts/install.sh" ] || [ ! -f "$source_dir/backend/piradar/__main__.py" ]; then
  echo "That download does not look like PiRadar. Nothing was changed." >&2
  exit 1
fi

# --- 2. Test before installing --------------------------------------------
echo "Running tests…"
if ! (cd "$source_dir" && PYTHONPATH=backend python3 -m unittest discover -s tests -q >"$work/tests.log" 2>&1); then
  tail -n 20 "$work/tests.log" >&2
  echo "Tests failed. Nothing was changed." >&2
  exit 1
fi

# --- 3. Back up the current install ---------------------------------------
if [ -d "$install_dir" ]; then
  rm -rf "$backup_dir"
  cp -a "$install_dir" "$backup_dir"
fi

# --- 4. Install, restart, verify ------------------------------------------
echo "Installing…"
if sh "$source_dir/scripts/install.sh" >"$work/install.log" 2>&1; then
  printf '%s (%s)\n' "$ref" "$(date -u +%Y-%m-%dT%H:%MZ)" >"$install_dir/VERSION"
  echo "Restarting PiRadar…"
  if restart_services; then
    echo "Update complete: $(cat "$install_dir/VERSION")"
    exit 0
  fi
  echo "The new version did not start. Rolling back." >&2
else
  # A half-finished install is as bad as a broken one: put the backup back.
  tail -n 20 "$work/install.log" >&2
  echo "The installer failed. Rolling back." >&2
fi

# --- 5. Automatic rollback -------------------------------------------------
if restore_backup; then
  echo "Rolled back to the previous version. The failed copy is in $install_dir.failed" >&2
else
  echo "Rollback also failed. Run: sudo $install_dir/scripts/update.sh --rollback" >&2
fi
exit 1
