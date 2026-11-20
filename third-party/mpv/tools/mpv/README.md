# Android libmpv 原生构建

主线独立增加 MPV 引擎。`libaurora_mpv_core.so` 是可替换的 LGPL 原生组件，导出完整上游 `mpv_*` C API 与三个 Android 环境/构建信息入口；`libaurora_mpv.so` 是应用自己的薄 JNI/输出适配层，动态链接该核心。两者不依赖、不替换现有 VLC/IJK 的 `libc++_shared.so`，核心内的 FFmpeg、C++ 和其它依赖符号不向应用进程导出。

固定源码和逐归档 SHA-256 在 `sources.lock.json`。MPV 0.42.0 使用 `gpl=false`；FFmpeg 9.0.2 使用 `disable-gpl`、`disable-nonfree`、`enable-version3`，与 Apache-2.0 的 mbedTLS 组合后按 LGPL-3.0-or-later 提供该核心。未启用 GPL 解码库、Lua、JavaScript、Vulkan、外部命令/下载工具。中文/ASS/位图字幕使用 libass；字体只从 Android 系统字体目录读取，字体缓存属于应用私有目录。

## 构建环境与复现

使用 Linux x86_64、Android NDK r28c（28.2.13676358）、CMake 4.1、Meson 1.11.0、Ninja、pkg-config、make、autoconf/automake/libtool、nasm、gperf 和 Python 3.8 以上。Meson 可从其官方 Python 制品安装到独立环境，`--meson` 指向该环境的可执行文件；如安装在自定义 `--target` 目录，需将其加入 `PYTHONPATH`。`--host-tools` 指向含 CMake 等宿主工具的目录。NDK 必须是 Linux 版本，不能指向 Windows NDK。脚本同时构建 `arm64-v8a` 与 `armeabi-v7a`，目标 API 21。

```bash
python3 tools/mpv/build_native.py \
  --ndk /opt/android-ndk-r28c \
  --host-tools /opt/build-tools/bin --meson /opt/python-tools/bin/meson \
  --downloads ./downloads --cache ./build-cache --output ./native \
  --stage dependencies --jobs 6

# 仅重建可替换的 LGPL 核心；此步骤不需要应用的 JNI 或 Kotlin 源码。
python3 tools/mpv/build_native.py \
  --ndk /opt/android-ndk-r28c \
  --host-tools /opt/build-tools/bin --meson /opt/python-tools/bin/meson \
  --downloads ./downloads --cache ./build-cache --output ./native --stage core
```

主线使用 `--stage all` 构建包括应用 JNI 的完整集合，或用 `--stage link` 在已有依赖上重新链接。公开对应源码附件只需 `dependencies`、`core` 两步。文件缓存目录和配置哈希不同会触发对应步骤，源码归档摘要不匹配会停止。修改第三方源码后请使用新的缓存目录/更新锁定归档，避免复用旧构建步骤。

Android 的 zlib/EGL/GLES 使用 NDK 系统头文件和链接桩，脚本生成相应 pkg-config 描述，不打包系统共享库。mbedTLS 的随机设备显式设置为 `/dev/urandom`。MPV 的构建期 Matroska Python 生成器延迟求值类型注解以兼容 Python 3.8。FFmpeg 的 HEVC MediaCodec 适配在缺少 VPS/SPS/PPS 配置时返回 `AVERROR_INVALIDDATA`，让 libmpv 处理解码器回退。上述源码变化都由 `prepare_sources` 实施，制品清单记录 MediaCodec 源文件摘要。

`tests/hevc_mediacodec_without_extradata.c` 可使用对应 ABI 的 Android NDK 编译器和 `pkg-config --static --libs libavcodec` 链接到静态 FFmpeg。在 Android 上执行时应返回成功，证明缺失参数会得到可处理的解码器打开错误。

## 对应材料与替换

直播硬解的 SurfaceView 和 TextureView 路径可使用 `mediacodec_embed` 直接向 Android Surface 输出；点播和显式软解继续使用 libmpv OpenGL。SurfaceView 只有在系统支持真实帧回调时才启用：Java MediaCodec 从 API 23 起支持，NDK 对应接口通过运行时符号检测（API 33 起提供）。TextureView 从 API 21 起使用逐缓冲时间戳与实际 View 更新交叉确认，解码提交本身不计作显示帧。不支持的输出能力在同一 MPV／解码方式下重建 GPU 输出，不启用软解回退。

`codec_output_hooks.inc` 和构建脚本的 FFmpeg 修改将每次文件打开的 `aurora_epoch` 原样交给输出观察器。显示帧还需匹配解码器令牌与当前 Surface；播放器销毁前先移除回调登记，因此迟到回调不能访问已释放实例或把上一台计作新台首帧。该可选接口不影响原有 `mpv_*` API；核心未提供接口时，客户端保留 GPU 路径。

`hardware_codec_selection.py/.inc` 保留 profile 优先选择。在 API 29 及以上，当厂商遗漏 profile 声明时，仅对系统明确标为硬件加速的视频组件补做 MIME 匹配；继续排除软件与要求安全／隧道模式的组件，真实配置与启动仍由系统决定。`codec_result_hooks.py/.inc` 观察选择、配置、启动及输出格式初始化的实际结果，并携带不可变的 `aurora_client` 和文件代次。客户端不会把原生状态值误当成 MPV 错误码；最终硬件失败会停止音频并解释失败格式和阶段，重建输出也始终保留用户选择的解码模式。

```bash
python3 tools/mpv/package_materials.py --downloads ./downloads --native ./native \
  --ndk /opt/android-ndk-r28c --output ./mpv-corresponding-source.zip
```

收集器验证全部源码和产物摘要，包含所有源码归档、构建/链接配方、Android 环境帮助函数、两 ABI 清单、原始许可证及 NDK 通知，并更新 APK 内通知目录。公开分发新版本时必须随对应 APK 提供此附件，不能只提供上游仓库链接。它不包含用户来源、配置、媒体、凭据或应用主体实现。

替换同 ABI 的 `lib/arm64-v8a/libaurora_mpv_core.so` 或 `lib/armeabi-v7a/libaurora_mpv_core.so`，保留公开 C API、Android 入口和 SONAME；薄 JNI 可继续使用 APK 原对象代码。核心导出表不锁定内容摘要，允许用户研究、修改和替换。重新打包、自签及必要调试权利见随包 `third_party/Library-replacement.md`。新增依赖时一并提供其兼容库和对应源码/许可。

## FCC 适配边界

仅已选中的 HTTP TS FCC 目标接入统一单连接预连接，HEAD 不消费媒体正文；不预测频道、不预开第二个解码器。同模式直播复用 mpv/GL 实例，`loadfile replace` 切换输入，保留旧输出缓冲。每个 playlist_entry_id 绑定独立输入代次；新输入视频参数就绪、实际新帧渲染、EGL 交换和 TextureView 对应时间戳同时成立才确认首帧。Prepared、Playing、旧画面重绘都不足以确认。

探测保留完整启动包，禁止 `nobuffer` 丢掉补送关键帧；当前使用 2 秒流信息分析上限、8 MiB 探测上限，完整参数已就绪时可提前结束，避免在高码率 HEVC 两组参数之间加入时因缺少 VPS/SPS/PPS 而无法启动。关闭启动阶段额外帧率采样，保留 0.1 秒预读和 50 ms 音频缓冲。GL 线程仍按 MPV 目标呈现时刻等待，保持 A/V 同步。直播暂停、后台、换源和释放取消旧网络，恢复由统一控制器管理。HLS/点播沿用鉴权、Range 回退、广告及原始时间轴模块。性能结论以实机记录为准，本地模拟 TS 不代表运营商 FCC 的回源与补流性能。

自动和硬解模式均仅使用 MediaCodec。软件解码只在手动选择时开启。直播硬解统一保留待送显帧，并在 HDR 转 SDR 时使用 Reinhard 色调映射降低 GPU 计算量。配置按每个输入传递，直播策略不会留在随后打开的点播输入上。首次启动 SDK 21–23 选择 TextureView，SDK 24 及以上选择 SurfaceView，设备配置保留已保存的选择。
