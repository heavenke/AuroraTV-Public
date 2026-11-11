# 第三方软件通知

适用于极光视界 Aurora TV **v1.0.0.1112**，整理日期为 2026-11-12。

极光视界应用主体采用闭源分发。下列第三方软件保留原作者版权及各自许可证，媒体容器、编解码、字幕、加密和网络等能力中包含这些组件的工作。应用主体与品牌的授权说明、第三方软件的授权范围分别依照其相应条款执行。

## 主要随包组件

| 组件或制品 | 版本与用途 | 许可及官方来源 |
| --- | --- | --- |
| AndroidX Core、AppCompat、Activity、Lifecycle、RecyclerView、ViewPager2 及其传递模块 | UI、生命周期、可访问性、分页与平台兼容 | Apache-2.0，[AndroidX](https://android.googlesource.com/platform/frameworks/support/) |
| Material Components for Android | 1.12.0，界面基础组件与主题 | Apache-2.0，[Material Components](https://github.com/material-components/material-components-android) |
| Kotlin 标准库与 kotlinx.coroutines | Kotlin 运行时、协程与 Android 调度，直接引用 coroutines 1.8.1 | Apache-2.0，[Kotlin](https://github.com/JetBrains/kotlin)、[kotlinx.coroutines](https://github.com/Kotlin/kotlinx.coroutines) |
| AndroidX Media3 | 1.6.1，ExoPlayer、HLS、UI 及 extractor、container、datasource 等传递模块 | Apache-2.0，[Media3 1.6.1](https://github.com/androidx/media/tree/1.6.1) |
| OkHttp 与 Okio | OkHttp 4.12.0 及其 Okio 依赖，HTTP、流与字节处理 | Apache-2.0，[OkHttp](https://github.com/square/okhttp/tree/parent-4.12.0)、[Okio](https://github.com/square/okio) |
| Gson | 2.11.0，JSON 处理 | Apache-2.0，[Gson](https://github.com/google/gson/tree/gson-parent-2.11.0) |
| ZXing Core | 3.5.3，二维码生成 | Apache-2.0，[ZXing](https://github.com/zxing/zxing/tree/zxing-3.5.3) |
| EdDSA-Java | `net.i2p.crypto:eddsa:0.3.0`，Ed25519 验签 | CC0-1.0，[EdDSA-Java](https://github.com/str4d/ed25519-java) |
| LibVLC Android | `org.videolan.android:libvlc-all:4.0.0-eap29`，VLC 引擎与 Java/JNI 接口 | LGPL-2.1，相关文件允许按其声明选择后续版本，[LibVLC Android](https://code.videolan.org/videolan/libvlcjni)、[VideoLAN](https://www.videolan.org/vlc/libvlc.html) |
| IJK Java 绑定的 GSY 维护制品 | `io.github.carguo:gsyijkjava:1.0.0` | 制品及相关 Java 文件为 Apache-2.0，原文件保留其各自声明，[GSYVideoPlayer](https://github.com/CarGuo/GSYVideoPlayer)、[IJK Java 绑定](https://github.com/CarGuo/ijkplayer/tree/30eb9441945da795079492041a791c121d2b8206/android/ijkplayer/ijkplayer-java) |
| IJK 原生维护制品 | `gsyvideoplayer-arm64:11.3.0`、`gsyvideoplayer-armv7a:11.3.0`，IJK、ijksdl、FFmpeg 等共享库 | IJK / FFmpeg 相关代码为 LGPL-2.1-or-later，各子组件按自身声明，[IJK](https://github.com/bilibili/ijkplayer)、[GSYVideoPlayer 11.3.0](https://github.com/CarGuo/GSYVideoPlayer/tree/v11.3.0) |
| OpenSSL | IJK ARM64 包含 1.1.1w，ARMv7 包含 1.0.2q | OpenSSL License 与 Original SSLeay License，[OpenSSL](https://github.com/openssl/openssl) |
| Android NDK libc++ 运行库 | 随 LibVLC AAR 提供的 `libc++_shared.so` | Apache-2.0 WITH LLVM-exception 及保留的历史条款，[LLVM libc++](https://github.com/llvm/llvm-project/tree/main/libcxx) |

AndroidX、Kotlin 和其它传递依赖随解析后的运行时一起使用。各项目内独立文件及所含依赖的授权声明继续有效，详细原始通知、源码与构建资料按照本版本的第三方资料清单查阅。

## LGPL 组件与用户权利

LibVLC、IJK 及其所含相关库以共享库形式提供，本发行版的两种 ARM ABI 原生库保留上游 SDK 制品字节。IJK 两个 ABI 的 FFmpeg 构建均声明 `--disable-gpl` 与 `--disable-nonfree`。GSY 制品的 Apache 发布元数据和各原生库的 LGPL 许可分别适用于对应代码。

使用者保留依据相应 LGPL 许可证复制、研究、修改和再分发这些库的权利，以及为使用修改后的库和调试相关修改所需的替换、重新链接与逆向工程权利。这些权利依相应许可证优先适用。完整条款见本仓库附带的许可证原文。[LGPL 2.1 原文](LICENSES/LGPL-2.1.txt)

本版本第三方库的源码、构建资料、原始版权通知及制品对应关系通过同版本 Release 的第三方资料附件提供。附件清单区分实际原生版本标识、上游提交、构建说明与来源证据。Android 应用业务实现的授权范围由应用自身说明确定。[同版本发布与第三方资料](https://github.com/heavenke/AuroraTV-Public/releases)

## 原生组件版本对应信息

| 制品部分 | 随包标识或上游对应信息 |
| --- | --- |
| LibVLC core | `4.0.0-dev-37538-gc84ef1eda4`，对应 VLC 提交 `c84ef1eda4f14f8b57a5b266b51c843cf51ed28b` |
| LibVLC JNI / Android 构建材料 | Android `libvlc-4.0.0-eap29` 标签所锁定的 JNI 提交 `a8d53a9151d7e4a9a5dfd0a5eb1cd92669afdc21` |
| IJK ARM64 | `k0.8.8-43-g30eb9441`，对应维护提交 `30eb9441945da795079492041a791c121d2b8206`；FFmpeg 构建标识 4.1.6 |
| IJK ARMv7 | `k0.8.8-32-ge99d640e`，对应维护提交 `e99d640e5fe94c65132379307f92d7180bcde8e7`；FFmpeg 构建标识 `4.0--ijk0.8.8--20210205--001` |

以上原生标识用于定位对应材料，构建分支和外部依赖版本按第三方资料附件内的逐项映射说明确定。[VLC core 提交](https://github.com/videolan/vlc/tree/c84ef1eda4f14f8b57a5b266b51c843cf51ed28b)、[IJK ARM64 提交](https://github.com/CarGuo/ijkplayer/tree/30eb9441945da795079492041a791c121d2b8206)、[IJK ARMv7 提交](https://github.com/CarGuo/ijkplayer/tree/e99d640e5fe94c65132379307f92d7180bcde8e7)

## Media3 组件改动通知

本发行版对 Media3 1.6.1 的 `androidx.media3.exoplayer.audio.AudioTrackPositionTracker` 构造过程进行了单点字节码转换。原构造器中反射查询 `AudioTrack.getLatency` 的调用被替换为空方法引用，后续沿用该组件已有的公开 `AudioTimestamp` / 播放头计时回退。其它媒体提取、字幕及播放功能继续由相应上游模块提供。此改动由 X-Team 在本发行版中应用，相关 Media3 代码仍受 Apache-2.0 许可约束。[上游原始文件](https://github.com/androidx/media/blob/1.6.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/audio/AudioTrackPositionTracker.java)

## OpenSSL 致谢

This product includes software developed by the OpenSSL Project for use in the OpenSSL Toolkit (http://www.openssl.org/).

This product includes cryptographic software written by Eric Young (eay@cryptsoft.com).

This product includes software written by Tim Hudson (tjh@cryptsoft.com).

OpenSSL Project、Eric Young 与 Tim Hudson 的原始版权、再分发条件和免责条款保存在对应许可证文件中。[OpenSSL 1.1.1w 许可证](LICENSES/OpenSSL-1.1.1w-LICENSE.txt)、[OpenSSL 1.0.2q 许可证](LICENSES/OpenSSL-1.0.2q-LICENSE.txt)

## 许可证原文与附带通知

- [Apache License 2.0](LICENSES/Apache-2.0.txt)
- [GNU Lesser General Public License 2.1](LICENSES/LGPL-2.1.txt)
- [CC0 1.0 Universal](LICENSES/CC0-1.0.txt)
- [LLVM libc++ 许可证与 LLVM exception](LICENSES/LLVM-libcxx-LICENSE.txt)
- [ZXing 上游 NOTICE](LICENSES/ZXing-NOTICE.txt)
- [原文来源与文件校验值](LICENSES/SOURCES.md)

源码包中的独立组件继续保留各自许可证、版权及 NOTICE 文件。媒体来源插件与其发布者的代码另按对应作者许可使用；用户自行配置后取得的 JAR 由对应来源提供。rtp2httpd 作为独立 HTTP TS 服务进行互操作，相关项目按其自己的发行许可提供。[rtp2httpd](https://github.com/stackia/rtp2httpd)

各第三方软件的担保和责任条款按所附原文执行。
