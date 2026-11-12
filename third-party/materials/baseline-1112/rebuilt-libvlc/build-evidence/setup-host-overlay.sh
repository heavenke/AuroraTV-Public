#!/usr/bin/env bash
set -euo pipefail
base=/root/.cache/aurora-vlc-lgpl/toolchains
original=$base/android-ndk-r28c
overlay=$base/android-ndk-r28c-wsl1
mkdir -p "$overlay"
for path in "$original"/*; do
    name=$(basename "$path")
    if [[ "$name" != toolchains && "$name" != build ]]; then
        ln -sfn "$path" "$overlay/$name"
    fi
done
cp -a "$original/build" "$overlay/"
mkdir -p "$overlay/toolchains/llvm/prebuilt/linux-x86_64/bin"
for path in "$original/toolchains/llvm/prebuilt/linux-x86_64"/*; do
    name=$(basename "$path")
    if [[ "$name" != bin ]]; then ln -sfn "$path" "$overlay/toolchains/llvm/prebuilt/linux-x86_64/$name"; fi
done
for path in "$original/toolchains/llvm/prebuilt/linux-x86_64/bin"/*; do
    ln -sfn "$path" "$overlay/toolchains/llvm/prebuilt/linux-x86_64/bin/$(basename "$path")"
done
gcc -shared -fPIC /mnt/d/AI_PROJECT/AuroraTV/artifacts/vlc-lgpl-build/clang-host-path.c -ldl -o "$base/clang-host-path.so"
for name in clang clang++ clang-cpp clang-19; do
    rm -f "$overlay/toolchains/llvm/prebuilt/linux-x86_64/bin/$name"
    cp /mnt/d/AI_PROJECT/AuroraTV/artifacts/vlc-lgpl-build/clang-host-wrapper.sh "$overlay/toolchains/llvm/prebuilt/linux-x86_64/bin/$name"
    chmod +x "$overlay/toolchains/llvm/prebuilt/linux-x86_64/bin/$name"
done
bin=$overlay/toolchains/llvm/prebuilt/linux-x86_64/bin
"$bin/aarch64-linux-android21-clang" -shared -fPIC /root/.cache/aurora-vlc-lgpl/probe.c -o /root/.cache/aurora-vlc-lgpl/probe.so -v
printf '#include <vector>\nextern "C" int cpp_probe(void) { std::vector<int> v(3); return v.size(); }\n' > /root/.cache/aurora-vlc-lgpl/probe.cpp
"$bin/aarch64-linux-android21-clang++" -shared -fPIC /root/.cache/aurora-vlc-lgpl/probe.cpp -o /root/.cache/aurora-vlc-lgpl/probe-cpp.so
file /root/.cache/aurora-vlc-lgpl/probe.so /root/.cache/aurora-vlc-lgpl/probe-cpp.so
"$bin/armv7a-linux-androideabi21-clang" -shared -fPIC /root/.cache/aurora-vlc-lgpl/probe.c -o /root/.cache/aurora-vlc-lgpl/probe-arm.so
"$bin/armv7a-linux-androideabi21-clang++" -shared -fPIC /root/.cache/aurora-vlc-lgpl/probe.cpp -o /root/.cache/aurora-vlc-lgpl/probe-arm-cpp.so
file /root/.cache/aurora-vlc-lgpl/probe-arm.so /root/.cache/aurora-vlc-lgpl/probe-arm-cpp.so
