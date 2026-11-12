#!/usr/bin/env bash
set -euo pipefail
ndk=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c
toolchain=$ndk/toolchains/llvm/prebuilt/linux-x86_64
for name in ld.lld llvm-ar llvm-nm llvm-objcopy llvm-readelf; do
  "$toolchain/bin/$name" --version | head -n 1 || true
done
printf '#include <stdio.h>\nint hello(void) { return puts("hello"); }\n' > /root/.cache/aurora-vlc-lgpl/probe.c
/lib64/ld-linux-x86-64.so.2 "$toolchain/bin/clang-19" -no-canonical-prefixes -fintegrated-cc1 -ccc-install-dir "$toolchain/bin" --target=aarch64-linux-android21 --sysroot="$toolchain/sysroot" -resource-dir "$toolchain/lib/clang/19" -B"$toolchain/bin" -fPIC -shared /root/.cache/aurora-vlc-lgpl/probe.c -o /root/.cache/aurora-vlc-lgpl/probe.so -v
file /root/.cache/aurora-vlc-lgpl/probe.so
