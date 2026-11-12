#!/usr/bin/env bash
# Rebuild the pinned eap29 dual-ARM native SDK in a Linux checkout.
set -euo pipefail

if [[ $# != 2 ]]; then
    echo "Usage: ANDROID_NDK=/path/to/ndk-r28c ANDROID_HOME=/path/to/sdk bash $0 /path/to/libvlcjni /path/to/output" >&2
    exit 2
fi
source_dir=$(realpath "$1")
output_dir=$(realpath -m "$2")
vlc_revision=c84ef1eda4f14f8b57a5b266b51c843cf51ed28b
script_dir=$(cd "$(dirname "$0")" && pwd -P)
test -n "${ANDROID_NDK:-}" && test -n "${ANDROID_HOME:-}"
test -f "$source_dir/buildsystem/compile-libvlc.sh"
if [[ -d "$source_dir/.git" ]]; then
    test "$(git -C "$source_dir" rev-parse HEAD)" = a8d53a9151d7e4a9a5dfd0a5eb1cd92669afdc21
fi
if [[ -d "$source_dir/vlc/.git" ]]; then
    test "$(git -C "$source_dir/vlc" rev-parse HEAD)" = "$vlc_revision"
else
    python3 "$script_dir/build_libvlc_lgpl_prepare.py" --verify-archive "$source_dir"
    # An extracted tree may live inside another Git repository. Limit discovery
    # so git apply operates on this source directory rather than its parent repo.
    export GIT_CEILING_DIRECTORIES="$source_dir"
fi
grep -q "VLC_TESTED_HASH=$vlc_revision" "$source_dir/buildsystem/get-vlc.sh"
mkdir -p "$output_dir/logs"
export LC_ALL=C
export MAKEFLAGS=${MAKEFLAGS:--j8}

# Official JNI patches are preserved in the matching source archive.
for patch in "$source_dir"/libvlc/patches/*.patch; do
    if git -C "$source_dir/vlc" apply --reverse --check "$patch" 2>/dev/null; then
        continue
    fi
    git -C "$source_dir/vlc" apply --check "$patch"
    git -C "$source_dir/vlc" apply "$patch"
done
for patch in "$script_dir"/patches/*.patch; do
    if git -C "$source_dir/vlc" apply --reverse --check "$patch" 2>/dev/null; then
        continue
    fi
    git -C "$source_dir/vlc" apply --check "$patch"
    git -C "$source_dir/vlc" apply "$patch"
done
python3 "$script_dir/build_libvlc_lgpl_prepare.py" "$source_dir"
if [[ ! -d "$source_dir/vlc/.git" ]]; then
    python3 "$script_dir/build_libvlc_lgpl_prepare.py" --record-prepared "$source_dir"
fi
(
    cd "$source_dir/vlc/extras/tools"
    ./bootstrap
    make $MAKEFLAGS
) > "$output_dir/logs/tools-build.log" 2>&1
export PATH="$source_dir/vlc/extras/tools/build/bin:$PATH"
if [[ ! -f "$source_dir/vlc/configure" ]]; then
    (cd "$source_dir/vlc" && ./bootstrap) > "$output_dir/logs/vlc-bootstrap.log" 2>&1
fi
for abi in arm64 arm; do
    (
        cd "$source_dir"
        ./buildsystem/compile-libvlc.sh -a "$abi" --release --license l
    ) > "$output_dir/logs/build-$abi.log" 2>&1
done
mkdir -p "$output_dir/native/arm64-v8a" "$output_dir/native/armeabi-v7a"
for abi in arm64-v8a armeabi-v7a; do
    for name in libvlc.so libvlcjni.so libc++_shared.so; do
        cp "$source_dir/libvlc/jni/libs/$abi/$name" "$output_dir/native/$abi/$name"
    done
done
if [[ -d "$source_dir/vlc/.git" ]]; then
    git -C "$source_dir/vlc" diff --binary > "$output_dir/vlc-build.patch"
fi
sha256sum "$output_dir"/native/*/*.so > "$output_dir/native-sha256.txt"
echo "Dual-ARM native SDK created in $output_dir/native. Run the module/license audit and package helper before distribution."
