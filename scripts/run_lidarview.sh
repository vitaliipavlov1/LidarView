#!/usr/bin/env bash
# Launch the LidarView 5.3.0 GUI from the local runtime.
# Any arguments are passed through to the LidarView binary.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LV_HOME="$ROOT/runtime/LidarView-5.3.0"
LV_BIN="$LV_HOME/bin/LidarView"
export LV_ROOT="$ROOT"   # so --script helpers can find data/

[[ -x "$LV_BIN" ]] || { echo "ERROR: LidarView binary not found at $LV_BIN" >&2
                        echo "Run: $ROOT/scripts/fetch.sh" >&2; exit 1; }

# Qt >= 6.5 needs libxcb-cursor.so.0 for its xcb platform plugin.
# Preferred permanent fix:  sudo apt install libxcb-cursor0
# Until then we use the copy staged under runtime/extra-libs/ (Ubuntu package).
if ! ldconfig -p 2>/dev/null | grep -q 'libxcb-cursor\.so\.0'; then
  if [[ -e "$ROOT/runtime/extra-libs/libxcb-cursor.so.0" ]]; then
    export LD_LIBRARY_PATH="$ROOT/runtime/extra-libs${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  else
    echo "WARNING: libxcb-cursor0 is missing system-wide and not staged in runtime/extra-libs/." >&2
    echo "         Qt will fail to start. Fix: sudo apt install libxcb-cursor0" >&2
  fi
fi

exec "$LV_BIN" "$@"
