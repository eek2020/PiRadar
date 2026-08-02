#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export PYTHONPATH="$project_dir/backend${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m piradar "$@"

