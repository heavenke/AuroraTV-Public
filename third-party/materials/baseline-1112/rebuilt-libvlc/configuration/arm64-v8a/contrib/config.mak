EXTRA_CFLAGS=-g -O2 -fPIC -fdata-sections -ffunction-sections -funwind-tables  -fstack-protector-strong -no-canonical-prefixes --start-no-unused-arguments -Wl,-z,max-page-size=16384 --end-no-unused-arguments -DNDEBUG 
EXTRA_CXXFLAGS=-fexceptions -frtti --start-no-unused-arguments -Wl,-z,max-page-size=16384 --end-no-unused-arguments -fdata-sections -ffunction-sections
EXTRA_LDFLAGS=-z max-page-size=16384
CC=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c-wsl1/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android21-clang
CXX=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c-wsl1/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android21-clang++
AR=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c-wsl1/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-ar
AS=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c-wsl1/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-as
RANLIB=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c-wsl1/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-ranlib
LD=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c-wsl1/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-ld
NM=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c-wsl1/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-nm
STRIP=/root/.cache/aurora-vlc-lgpl/toolchains/android-ndk-r28c-wsl1/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip
