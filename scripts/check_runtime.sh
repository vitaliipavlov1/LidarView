#!/usr/bin/env bash
# Verify the LidarView runtime is complete and launchable.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LV_HOME="$ROOT/runtime/LidarView-5.3.0"
fails=0
ok()   { printf '  [ OK ] %s\n' "$1"; }
bad()  { printf '  [FAIL] %s\n' "$1"; fails=$((fails+1)); }
warn() { printf '  [WARN] %s\n' "$1"; }

echo "== executables =="
for exe in LidarView lvpython lvbatch lvserver PacketFileSender; do
  [[ -x "$LV_HOME/bin/$exe" ]] && ok "bin/$exe" || bad "bin/$exe missing"
done

echo "== required components =="
for f in "lib/paraview-6.1/plugins/paraview.plugins.xml" \
         "lib/lidarview/plugins/lidarview.plugins.xml" \
         "lib/slam/plugins/slam.plugins.xml" \
         "lib/slam/plugins/LidarSlamPlugin/LidarSlamPlugin.so" \
         "share/HDL_32.xml" "share/VLP_16.xml"; do
  [[ -e "$LV_HOME/$f" ]] && ok "$f" || bad "$f missing"
done
n=$(grep -c '<Plugin ' "$LV_HOME/lib/lidarview/plugins/lidarview.plugins.xml" 2>/dev/null)
ok "lidarview plugin manifest lists $n plugins"

echo "== shared libraries =="
if ldconfig -p 2>/dev/null | grep -q 'libxcb-cursor\.so\.0'; then
  ok "libxcb-cursor.so.0 present system-wide"
  export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
elif [[ -e "$ROOT/runtime/extra-libs/libxcb-cursor.so.0" ]]; then
  warn "libxcb-cursor0 not installed system-wide; using runtime/extra-libs/ (fix: sudo apt install libxcb-cursor0)"
  export LD_LIBRARY_PATH="$ROOT/runtime/extra-libs${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
else
  bad "libxcb-cursor.so.0 not found anywhere -- Qt cannot start (sudo apt install libxcb-cursor0)"
fi
for target in "bin/LidarView" "lib/slam/plugins/LidarSlamPlugin/LidarSlamPlugin.so"; do
  miss=$(LD_LIBRARY_PATH="$LV_HOME/lib:${LD_LIBRARY_PATH:-}" ldd "$LV_HOME/$target" 2>/dev/null | grep -c 'not found')
  [[ "$miss" -eq 0 ]] && ok "$target: all dependencies resolved" || bad "$target: $miss unresolved libraries"
done

echo "== version =="
ver=$(timeout 120 "$LV_HOME/bin/LidarView" --version 2>/dev/null | tr -d '\r')
[[ -n "$ver" ]] && ok "LidarView 5.3.0 reports core: $ver" || bad "could not obtain version"

echo "== headless python runtime =="
out=$(timeout 180 "$LV_HOME/bin/lvpython" -c \
  "from paraview.simple import *; print('lvpython', GetParaViewVersion()); print('SLAM proxy:', 'SLAMonline' in dir())" 2>/dev/null)
[[ -n "$out" ]] && ok "lvpython works -> $(echo "$out" | tr '\n' ' ')" || bad "lvpython failed"

echo "== display =="
[[ -n "${DISPLAY:-}" ]] && ok "DISPLAY=$DISPLAY" || warn "DISPLAY not set -- GUI cannot open"
if command -v glxinfo >/dev/null; then
  gl=$(timeout 30 glxinfo -B 2>/dev/null | grep -m1 'OpenGL core profile version')
  [[ -n "$gl" ]] && ok "${gl# }" || warn "no OpenGL core profile reported"
fi

echo
[[ "$fails" -eq 0 ]] && echo "RESULT: PASS - runtime is complete" || echo "RESULT: FAIL - $fails problem(s)"
exit $(( fails > 0 ))
