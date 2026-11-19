# 当前公众版的 MPV 对应材料

v1.0.7.261119 使用 MPV 0.42.0 单引擎。核心为独立、可替换的 `libaurora_mpv_core.so`，涵盖 ARM64 与 ARM32，构建目标 Android API 21。应用主体与薄 JNI 不属于这里公开的第三方核心源码。

- `downloads/`：已经核验的原始第三方源码归档，获取地址、固定版本与 SHA-256 见 `tools/mpv/sources.lock.json`。
- `tools/mpv/`：核心构建配方、Android 环境入口、导出表、兼容补丁与独立回归。
- `licenses/`：实际组件的原始版权、许可和 NDK 通知。
- `manifests/`：两 ABI 的核心与薄 JNI 摘要，对应当前 APK。
- `SHA256SUMS`：本目录对应材料的文件校验表。

MPV 关闭 GPL，FFmpeg 关闭 GPL/nonfree 并启用 version3，组合核心按 LGPL-3.0-or-later 提供。各依赖仍保留自身条款。缺少 HEVC 配置数据时返回可处理错误的兼容改动，由构建配方在准备源码时应用。

## 重构建和替换

在 Linux 上准备 Android NDK r28c、Python 3、Meson、Ninja、CMake、pkg-config、Autoconf、Automake、Libtool 等工具，按 [完整原生构建说明](tools/mpv/README.md) 安装固定构建工具。原配方的默认工具路径可通过参数覆盖。

```sh
python3 tools/mpv/build_native.py --stage core \
  --ndk /opt/android-ndk-r28c \
  --downloads ./downloads --output ./rebuilt-core \
  --meson /path/to/meson --host-tools /path/to/build-tools
```

`--stage core` 仅重构建 LGPL 核心，不需要应用主体或薄 JNI 源码。保留同 ABI 的 SONAME、公开 MPV C API 和 Android 环境入口，将重构建的核心替换 APK 中对应库，再重新打包、自签即可。原薄 JNI 对象代码已包含在 APK 的 `libaurora_mpv.so` 中，可继续与兼容核心动态链接。

相应修改、调试、重新链接与替换权利不受应用主体版权声明限制。完整权利说明见 [库替换说明](../../Library-replacement.md)。历史版本使用的其他组件材料继续保留归档，不能据此判断当前 APK 仍包含那些引擎。
