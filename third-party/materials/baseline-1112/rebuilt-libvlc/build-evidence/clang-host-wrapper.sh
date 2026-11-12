#!/usr/bin/env bash
set -euo pipefail
original=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c/toolchains/llvm/prebuilt/linux-x86_64
overlay=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c-wsl1/toolchains/llvm/prebuilt/linux-x86_64
export AURORA_CLANG_HOST_ENTRY="$overlay/bin/clang-19"
export LD_PRELOAD=/root/.cache/aurora-vlc-lgpl/toolchains/clang-host-path.so
if [[ "${1:-}" == -cc1 || "${1:-}" == -cc1as ]]; then
    exec /lib64/ld-linux-x86-64.so.2 "$original/bin/clang-19" "$@"
fi
mode=()
case "$(basename "$0")" in
  clang++) mode=(--driver-mode=g++) ;;
  clang-cpp) mode=(--driver-mode=cpp) ;;
esac
exec /lib64/ld-linux-x86-64.so.2 "$original/bin/clang-19" \
    "${mode[@]}" -ccc-install-dir "$overlay/bin" \
    -resource-dir "$original/lib/clang/19" --sysroot="$original/sysroot" \
    -B"$overlay/bin" -B"$original/bin" "$@" -canonical-prefixes
