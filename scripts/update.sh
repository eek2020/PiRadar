#!/usr/bin/env sh
# ---------------------------------------------------------------------------
# PiRadar over-the-air updater
#
# Installs a version of PiRadar from GitHub, with a safety net:
#   1. resolve the channel (a branch or tag) to an exact commit
#   2. download that commit and run the test suite (nothing installed yet)
#   3. back up the current install to /opt/piradar.previous
#   4. run the normal installer, restart the service, check /api/health
#   5. if anything fails, put the backup back automatically
#
# Normally this runs by itself, as systemd units:
#   piradar-update.service       "Install update" on the touchscreen
#   piradar-update-auto.service  every 15 minutes (piradar-update.timer);
#                                on by default, can be switched off on screen
#
# So a Pi anywhere, behind any router, updates itself: push to GitHub and it
# installs the new commit within about 15 minutes. If an update needs a
# restart (for example a boot setting), automatic and button runs restart the
# Pi themselves, at most once per version so a restart can never loop.
#
# It can also be run by hand:
#   sudo /opt/piradar/scripts/update.sh                # follow the current channel
#   sudo /opt/piradar/scripts/update.sh some-branch    # switch channel and update
#   sudo /opt/piradar/scripts/update.sh --if-newer     # skip if already current
#   sudo /opt/piradar/scripts/update.sh --auto         # what the timer runs
#   sudo /opt/piradar/scripts/update.sh --rollback     # undo the last update
#
# The channel is remembered in /etc/piradar/update-channel (default: main).
# Progress is written to /var/lib/piradar-update/status.json for the app.
# Settings in /etc/piradar and /var/lib/piradar are never touched.
# ---------------------------------------------------------------------------
set -eu

repo=${PIRADAR_REPO:-eek2020/PiRadar}
install_dir=/opt/piradar
backup_dir=/opt/piradar.previous
config_file=/etc/piradar/piradar.json
channel_file=/etc/piradar/update-channel
status_dir=/var/lib/piradar-update
status_file="$status_dir/status.json"
app_settings=/var/lib/piradar/update-settings.json
# Records the version the Pi last restarted for, so restarts cannot loop.
reboot_marker="$status_dir/rebooted-for"
lock_file=${PIRADAR_UPDATE_LOCK:-/run/piradar-update.lock}

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

# Only one update at a time: the button and the timer use separate units, so
# they could otherwise overlap. A second run simply steps aside.
exec 9>"$lock_file"
if ! flock -n 9; then
  rm -f "$PIRADAR_UPDATER_COPY"
  echo "Another update is already running."
  exit 0
fi

ref=""
sha=""
# Automatic checks stay silent until they find something to install, so the
# screen does not flash "Checking…" every 15 minutes.
quiet=0

# Record progress for the touchscreen. Python does the JSON escaping and an
# atomic write, so the app never reads a half-written file.
write_status() {
  [ "$quiet" = 1 ] && return 0
  install -d -m 0755 "$status_dir"
  python3 - "$status_file" "$1" "$2" "$ref" "$sha" <<'PY'
import json, os, sys, tempfile, time
path, state, message, ref, sha = sys.argv[1:6]
payload = {"state": state, "message": message, "ref": ref, "sha": sha,
           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
handle, temporary = tempfile.mkstemp(dir=os.path.dirname(path))
with os.fdopen(handle, "w") as stream:
    json.dump(payload, stream)
os.chmod(temporary, 0o644)
os.replace(temporary, path)
PY
}

# Print a value from a small JSON file, or nothing if it is missing.
json_value() {
  python3 - "$1" "$2" <<'PY' 2>/dev/null || true
import json, sys
try:
    value = json.load(open(sys.argv[1])).get(sys.argv[2])
except Exception:
    value = None
if value is not None:
    print(str(value).lower() if isinstance(value, bool) else value)
PY
}

# Health check URL: use the port from the Pi's config, defaulting to 8080.
port=$(json_value "$config_file" port)
health_url="http://127.0.0.1:${port:-8080}/api/health"

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

# Does the Pi need a restart for a PiRadar boot setting to take effect?
# Compare only the boot options PiRadar manages: the firmware adds and
# rewrites others, so the whole line never matches exactly.
restart_needed() {
  boot_line=/boot/firmware/cmdline.txt
  [ -f "$boot_line" ] || boot_line=/boot/cmdline.txt
  [ -f "$boot_line" ] || return 1
  on_disk=" $(head -n 1 "$boot_line" | tr -d '\r\n') "
  running=" $(cat /proc/cmdline 2>/dev/null) "
  for managed in brcmfmac.feature_disable=0x82000 logo.nologo vt.global_cursor_default=0; do
    case "$on_disk" in *" $managed "*)
      case "$running" in *" $managed "*) ;; *) return 0 ;; esac ;;
    esac
  done
  return 1
}

# Restart the Pi to finish, unless it has already restarted for this
# version (so a setting that never takes effect cannot cause a restart loop).
# $1 is the message to show. Returns 1 if no restart was started.
restart_pi_once() {
  [ "$(cat "$reboot_marker" 2>/dev/null)" != "$sha" ] || return 1
  install -d -m 0755 "$status_dir"
  printf '%s\n' "$sha" >"$reboot_marker"
  quiet=0
  write_status success "$1"
  echo "$1."
  systemctl reboot --no-block
}

# Stop with a message on screen and in the status file.
fail() {
  echo "$1" >&2
  write_status failed "$1"
  exit 1
}

# --- Options ---------------------------------------------------------------
mode=manual
case "${1:-}" in
  --rollback)
    rm -f "$PIRADAR_UPDATER_COPY"
    write_status rolling_back "Restoring the previous version"
    if restore_backup; then
      write_status rolled_back "Rolled back to the previous version"
      echo "Rolled back to: $(cat "$install_dir/VERSION" 2>/dev/null || echo 'previous version')"
      exit 0
    fi
    fail "Rollback failed"
    ;;
  --auto) mode=auto; quiet=1 ;;
  --if-newer) mode=if-newer ;;
  "") ;;
  -*) echo "Unknown option: $1" >&2; exit 1 ;;
  *)
    # An explicit branch or tag becomes the channel to follow from now on.
    install -d -m 0755 "$(dirname "$channel_file")"
    printf '%s\n' "$1" >"$channel_file"
    ;;
esac

# Automatic updates are on unless someone switched them off on the screen.
if [ "$mode" = auto ] && [ "$(json_value "$app_settings" auto)" = "false" ]; then
  echo "Automatic updates are switched off."
  exit 0
fi

ref=$(head -n 1 "$channel_file" 2>/dev/null | tr -d '[:space:]' || true)
ref=${ref:-main}
work=$(mktemp -d)
trap 'rm -rf "$work" "$PIRADAR_UPDATER_COPY"' EXIT

# --- 1. Resolve the channel to an exact commit -----------------------------
write_status checking "Checking GitHub for $ref"
echo "Checking $repo at $ref…"
if ! curl -fsSL --retry 2 -H "Accept: application/vnd.github+json" \
    -o "$work/commit.json" "https://api.github.com/repos/$repo/commits/$ref"; then
  fail "Could not reach GitHub, or $ref does not exist"
fi
sha=$(json_value "$work/commit.json" sha)
[ -n "$sha" ] || fail "GitHub did not return a commit for $ref"

installed_sha=$(json_value "$install_dir/VERSION.json" sha)
if [ "$mode" != manual ] && [ "$sha" = "$installed_sha" ]; then
  # An earlier install may still be waiting for a restart, for example one
  # done by an older updater that could not restart the Pi. Finish it now.
  if restart_needed && restart_pi_once "Updated to $(printf '%.7s' "$sha"). Restarting the Pi to finish"; then
    exit 0
  fi
  write_status up_to_date "Already up to date"
  echo "Already up to date ($(printf '%.7s' "$sha"))."
  exit 0
fi
# Automatic and button-started runs never go backwards. If the channel is
# behind what is installed (for example main before a branch is merged),
# stay put. Running by hand with a branch name can still downgrade on purpose.
if [ "$mode" != manual ] && [ -n "$installed_sha" ]; then
  if curl -fsSL --retry 2 -H "Accept: application/vnd.github+json" -o "$work/compare.json" \
      "https://api.github.com/repos/$repo/compare/$installed_sha...$sha"; then
    if [ "$(json_value "$work/compare.json" status)" = "behind" ]; then
      write_status up_to_date "Installed version is newer than $ref"
      echo "Installed version is newer than $ref. Nothing to do."
      exit 0
    fi
  else
    # GitHub reached a moment ago, so this means it does not know the
    # installed commit (for example its branch was deleted). It cannot be
    # shown to be newer, so carry on rather than blocking updates for ever.
    echo "Installed commit is unknown to GitHub; updating anyway." >&2
  fi
fi

# --- 2. Download and test before installing --------------------------------
# From here on there is a real update in progress, so report it.
quiet=0
write_status downloading "Downloading $(printf '%.7s' "$sha")"
echo "Downloading $(printf '%.7s' "$sha")…"
curl -fsSL --retry 3 -o "$work/source.tgz" "https://github.com/$repo/archive/$sha.tar.gz" \
  || fail "Download failed"
tar -xzf "$work/source.tgz" -C "$work"
source_dir=$(find "$work" -mindepth 1 -maxdepth 1 -type d | head -n 1)
if [ ! -f "$source_dir/scripts/install.sh" ] || [ ! -f "$source_dir/backend/piradar/__main__.py" ]; then
  fail "That download does not look like PiRadar. Nothing was changed"
fi

write_status testing "Running tests"
echo "Running tests…"
if ! (cd "$source_dir" && PYTHONPATH=backend python3 -m unittest discover -s tests -q >"$work/tests.log" 2>&1); then
  tail -n 20 "$work/tests.log" >&2
  fail "Tests failed. Nothing was changed"
fi

# --- 3. Back up the current install ---------------------------------------
if [ -d "$install_dir" ]; then
  rm -rf "$backup_dir"
  cp -a "$install_dir" "$backup_dir"
fi

# --- 4. Install, restart, verify ------------------------------------------
write_status installing "Installing"
echo "Installing…"
if sh "$source_dir/scripts/install.sh" >"$work/install.log" 2>&1; then
  printf '%s %.7s (%s)\n' "$ref" "$sha" "$(date -u +%Y-%m-%dT%H:%MZ)" >"$install_dir/VERSION"
  python3 - "$install_dir/VERSION.json" "$ref" "$sha" <<'PY'
import json, sys, time
json.dump({"ref": sys.argv[2], "sha": sys.argv[3],
           "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
          open(sys.argv[1], "w"))
PY
  write_status restarting "Restarting PiRadar"
  echo "Restarting PiRadar…"
  if restart_services; then
    # If the boot splash has been installed (an opt-in step), keep it in step
    # with the update. Only rebuild when the theme actually changed, because
    # that means rebuilding the initramfs. A splash problem never fails the
    # update: the radar itself is already running the new version.
    splash_theme=/usr/share/plymouth/themes/piradar
    if [ -d "$splash_theme" ] && [ -d "$install_dir/boot/plymouth/piradar" ] \
      && ! diff -rq "$install_dir/boot/plymouth/piradar" "$splash_theme" >/dev/null 2>&1; then
      echo "Refreshing the boot splash…"
      sh "$install_dir/scripts/install-splash.sh" >/dev/null \
        || echo "Warning: the boot splash could not be refreshed. Run install-splash.sh by hand." >&2
    fi
    # Some changes (such as Wi-Fi compatibility mode) only apply after the Pi
    # restarts. Button and automatic runs restart it themselves; a run by
    # hand over SSH leaves the restart to the person running it.
    finished="Updated to $(printf '%.7s' "$sha")"
    if restart_needed; then
      if [ "$mode" != manual ] && restart_pi_once "$finished. Restarting the Pi to finish"; then
        exit 0
      fi
      finished="$finished. Restart PiRadar to finish: Map options, Power, Restart"
    fi
    write_status success "$finished"
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
write_status rolling_back "The new version did not start. Restoring the previous one"
if restore_backup; then
  write_status rolled_back "The update did not start, so the previous version was restored"
  echo "Rolled back to the previous version. The failed copy is in $install_dir.failed" >&2
else
  write_status failed "Rollback failed. Run update.sh --rollback by hand"
  echo "Rollback also failed. Run: sudo $install_dir/scripts/update.sh --rollback" >&2
fi
exit 1
