# ---------------------------------------------------------------------------
# Shared helpers for editing the Raspberry Pi boot files safely.
#
# Sourced by install-splash.sh and wifi-compat.sh. Each tool adds and removes
# only its own kernel options, so they never undo each other's changes (a
# whole-file restore would). Every write goes through a temporary file and a
# rename, so a power cut cannot leave a half-written boot file.
#
# PIRADAR_BOOT_DIR overrides the boot directory, which the tests use.
# ---------------------------------------------------------------------------

boot_dir=${PIRADAR_BOOT_DIR:-}
if [ -z "$boot_dir" ]; then
  # Trixie keeps boot files in /boot/firmware; older releases used /boot.
  if [ -f /boot/firmware/cmdline.txt ]; then boot_dir=/boot/firmware; else boot_dir=/boot; fi
fi
cmdline="$boot_dir/cmdline.txt"
config="$boot_dir/config.txt"

# replace_file TARGET < new-content
replace_file() {
  _target=$1
  _temporary="$_target.piradar-new"
  cat >"$_temporary"
  sync "$_temporary" 2>/dev/null || sync
  mv "$_temporary" "$_target"
}

# Keep one copy of the file as it was before PiRadar first touched it.
backup_once() {
  [ -e "$1.piradar-bak" ] || cp -p "$1" "$1.piradar-bak"
}

# The kernel command line is a single line; read it without the newline.
cmdline_read() {
  head -n 1 "$cmdline" | tr -d '\r\n'
}

cmdline_has() {
  case " $(cmdline_read) " in
    *" $1 "*) return 0 ;;
    *) return 1 ;;
  esac
}

# cmdline_add OPTION...  prints the options it actually added (one per line)
cmdline_add() {
  _line=$(cmdline_read)
  _updated=$_line
  for _option in "$@"; do
    case " $_updated " in
      *" $_option "*) ;;
      *) _updated="$_updated $_option"; printf '%s\n' "$_option" ;;
    esac
  done
  if [ "$_updated" != "$_line" ]; then
    backup_once "$cmdline"
    printf '%s\n' "$_updated" | replace_file "$cmdline"
  fi
}

# cmdline_remove OPTION...
cmdline_remove() {
  _line=$(cmdline_read)
  _updated=""
  # set -f: split on spaces only, never expand * or ? in an option as a glob.
  set -f
  for _word in $_line; do
    _keep=1
    for _option in "$@"; do
      [ "$_word" = "$_option" ] && _keep=0
    done
    [ "$_keep" = 1 ] && _updated="${_updated:+$_updated }$_word"
  done
  set +f
  if [ "$_updated" != "$_line" ]; then
    printf '%s\n' "$_updated" | replace_file "$cmdline"
  fi
}
