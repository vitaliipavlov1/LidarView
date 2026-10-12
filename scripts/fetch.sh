#!/usr/bin/env bash
# Download + verify the LidarView release and the sample datasets.
# Skips anything already present with a matching checksum. Nothing here is committed to git.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LV_VERSION="5.3.0"
LV_URL="https://gitlab.kitware.com/api/v4/projects/4817/packages/generic/LidarView/v${LV_VERSION}/LidarView-${LV_VERSION}.tar.gz"
LV_SHA256="9daad12400e70031b1218358b15b023e90e4f7e454682a85af909da61d356b96"

# Kitware "Velodyne LiDAR" sample collection on data.kitware.com
DATA_URL_1="https://data.kitware.com/api/v1/file/5b7fff5e8d777f06857cb538/download"
DATA_NAME_1="HDL32-V2_Tunnel.pcap"
DATA_SHA512_1="5a61054d1ce0d789c02240caf169e0892e3c5f9ae11ceddbb16edd34b045c9a6426e9cd541bbd2fc4c12cabc6987292fda6cb778a6e358000601c2ffb42ec676"
DATA_URL_2="https://data.kitware.com/api/v1/file/5b7fff078d777f06857cb535/download"
DATA_NAME_2="HDL32-V2_R into Butterfield into Digital Drive.pcap"
DATA_SHA512_2="01324c432926867f1fb05943abf31064385f5fb8b7ee1e865e40140c96d4fc022ffdf22d2a3b5709e6e37b8cc9a99cc75fd8dd1d48f0f8eac48b564aef126ee2"

fetch() {  # url dest algo expected
  local url="$1" dest="$2" algo="$3" want="$4"
  if [[ -f "$dest" ]]; then
    echo "checking existing $(basename "$dest") ..."
    [[ "$("${algo}sum" "$dest" | cut -d' ' -f1)" == "$want" ]] && { echo "  OK (checksum matches, skipping)"; return 0; }
    echo "  checksum mismatch -- re-downloading"
  fi
  echo "downloading $(basename "$dest") ..."
  curl -SL --retry 3 --retry-delay 5 -C - -o "$dest" "$url" || return 1
  local got; got="$("${algo}sum" "$dest" | cut -d' ' -f1)"
  [[ "$got" == "$want" ]] && { echo "  OK ($algo verified)"; return 0; }
  echo "  FAIL: $algo mismatch"; echo "    expected $want"; echo "    got      $got"; return 1
}

mkdir -p "$ROOT/runtime/download" "$ROOT/data"
rc=0
fetch "$LV_URL" "$ROOT/runtime/download/LidarView-${LV_VERSION}.tar.gz" sha256 "$LV_SHA256" || rc=1

if [[ ! -x "$ROOT/runtime/LidarView-${LV_VERSION}/bin/LidarView" && $rc -eq 0 ]]; then
  echo "extracting LidarView-${LV_VERSION} ..."
  tar xzf "$ROOT/runtime/download/LidarView-${LV_VERSION}.tar.gz" -C "$ROOT/runtime" && echo "  OK"
fi

fetch "$DATA_URL_1" "$ROOT/data/$DATA_NAME_1" sha512 "$DATA_SHA512_1" || rc=1
fetch "$DATA_URL_2" "$ROOT/data/$DATA_NAME_2" sha512 "$DATA_SHA512_2" || rc=1

# Qt >= 6.5 needs libxcb-cursor0. Prefer the system package; otherwise stage it locally.
if ! ldconfig -p 2>/dev/null | grep -q 'libxcb-cursor\.so\.0'; then
  if [[ ! -e "$ROOT/runtime/extra-libs/libxcb-cursor.so.0" ]]; then
    echo "staging libxcb-cursor0 (preferred fix: sudo apt install libxcb-cursor0) ..."
    tmp="$(mktemp -d)"
    ( cd "$tmp" && apt-get download libxcb-cursor0 >/dev/null 2>&1 \
      && dpkg-deb -x ./*.deb x ) \
      && mkdir -p "$ROOT/runtime/extra-libs" \
      && cp -a "$tmp"/x/usr/lib/*/libxcb-cursor.so.* "$ROOT/runtime/extra-libs/" \
      && echo "  OK -> runtime/extra-libs/" || echo "  FAILED -- run: sudo apt install libxcb-cursor0"
    rm -rf "$tmp"
  fi
fi

echo
[[ $rc -eq 0 ]] && echo "RESULT: PASS - everything downloaded and verified" || echo "RESULT: FAIL"
exit $rc
