#!/usr/bin/env bash
set -euo pipefail
base=/root/.cache/aurora-vlc-lgpl
source=$base/source
export ANDROID_NDK=$base/toolchains/android-ndk-r28c-wsl1
export ANDROID_HOME=/mnt/d/Android_Project/Androkd_SDK
export PATH="$source/vlc/extras/tools/build/bin:$PATH"
export MAKEFLAGS=-j16
export LC_ALL=C
mkdir -p "$base/logs"
if [[ ! -f "$base/official-android-patches-applied" ]]; then
  git -C "$source/vlc" apply --check "$source"/libvlc/patches/*.patch
  git -C "$source/vlc" apply "$source"/libvlc/patches/*.patch
  git -C "$source/vlc" diff --binary > /mnt/d/AI_PROJECT/AuroraTV/artifacts/vlc-lgpl-build/official-android-patches.diff
  sha256sum "$source"/libvlc/patches/*.patch > /mnt/d/AI_PROJECT/AuroraTV/artifacts/vlc-lgpl-build/official-android-patches.sha256
  touch "$base/official-android-patches-applied"
fi
if [[ ! -f "$source/vlc/configure" ]]; then
  (cd "$source/vlc" && ./bootstrap) > "$base/logs/vlc-bootstrap.log" 2>&1
fi
cd "$source"
for abi in arm64 arm; do
  echo "Starting official LGPL profile build $abi $(date -u +%FT%TZ)"
  if [[ -f "$base/logs/build-$abi.log" ]]; then cp "$base/logs/build-$abi.log" "$base/logs/build-$abi.previous.log"; fi
  ./buildsystem/compile-libvlc.sh -a "$abi" --release --license l > "$base/logs/build-$abi.log" 2>&1
  echo "Finished official LGPL profile build $abi $(date -u +%FT%TZ)"
done
