# 第三方软件通知

本清单记录极光视界 Aurora TV 使用的第三方组件。各发行包的组件版本以随包通知和对应校验清单为准。

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
| dexlib2 | `org.smali:dexlib2:2.5.2`，在私有派生缓存中适配第三方接口的常规 Toast 调用，保留下载原件及其校验身份 | BSD-3-Clause，部分 AOSP 文件为 Apache-2.0，[固定版本源码](https://github.com/JesusFreke/smali/tree/v2.5.2/dexlib2)、[完整上游通知](LICENSES/dexlib2-NOTICE.txt) |
| Guava Android | `com.google.guava:guava:33.3.1-android`，DEX 读写所需集合与基础工具 | Apache-2.0，[固定版本源码](https://github.com/google/guava/tree/v33.3.1/android) |
| JSR-305 注解 | `com.google.code.findbugs:jsr305:3.0.2`，dexlib2 的注解依赖 | Apache-2.0，[固定来源制品及源码](https://repo.maven.apache.org/maven2/com/google/code/findbugs/jsr305/3.0.2/) |
| core-js 与 Babel 生成的运行时辅助代码 | 内置配置页的 ES5 与 Promise、集合兼容，支持 Android 5.0 WebView | MIT，[原始版权与许可](LICENSES/Config-web-runtime-LICENSE.txt) |
| LibVLC Android 派生 SDK | 基于 `libvlc-all:4.0.0-eap29` 对应固定源码重构建的双 ARM 版本，VLC 引擎与 Java/JNI 接口 | 官方 `l` 构建配置，LGPL-3.0-or-later 与所含组件各自的授权、附加致谢条款；Java/JNI 文件保留原声明，[LibVLC Android](https://code.videolan.org/videolan/libvlcjni)、[VideoLAN](https://www.videolan.org/vlc/libvlc.html) |
| LibVLC 所含 libass、FreeType、HarfBuzz 与 FriBidi | libass 0.17.4、FreeType 2.13.1、HarfBuzz 11.5.0、FriBidi 1.0.16，字幕与字体渲染 | 分别保留 ISC、FreeType License、Old MIT、LGPL 及各独立文件声明，[组件版权与许可原文](LICENSES/VLC-contrib-NOTICES.txt) |
| IJK Java 绑定的 GSY 维护制品 | `io.github.carguo:gsyijkjava:1.0.0` | 制品及相关 Java 文件为 Apache-2.0，原文件保留其各自声明，[GSYVideoPlayer](https://github.com/CarGuo/GSYVideoPlayer)、[IJK Java 绑定](https://github.com/CarGuo/ijkplayer/tree/30eb9441945da795079492041a791c121d2b8206/android/ijkplayer/ijkplayer-java) |
| IJK 原生维护制品 | `gsyvideoplayer-arm64:11.3.0`、`gsyvideoplayer-armv7a:11.3.0`，IJK、ijksdl、FFmpeg 等共享库 | IJK / FFmpeg 相关代码为 LGPL-2.1-or-later，各子组件按自身声明，[IJK](https://github.com/bilibili/ijkplayer)、[GSYVideoPlayer 11.3.0](https://github.com/CarGuo/GSYVideoPlayer/tree/v11.3.0) |
| OpenSSL | IJK ARM64 包含 1.1.1w，ARMv7 包含 1.0.2q | OpenSSL License 与 Original SSLeay License，[OpenSSL](https://github.com/openssl/openssl) |
| Android NDK C++ 运行库 | NDK r28c `28.2.13676358` 的双 ARM `libc++_shared.so`，Clang 19.0.1、LLVM 固定提交 `97a699bf4812a18fb657c2779f5296a4ab2694d2` | libc++、libc++abi、libunwind 的 Apache-2.0 WITH LLVM-exception 及保留的历史条款，[Android LLVM 对应源码](https://android.googlesource.com/toolchain/llvm-project/+/97a699bf4812a18fb657c2779f5296a4ab2694d2/) |

AndroidX、Kotlin 和其它传递依赖随解析后的运行时一起使用。各项目内独立文件及所含依赖的授权声明继续有效，详细原始通知、源码与构建资料按照本版本的第三方资料清单查阅。

## LGPL 组件与用户权利

LibVLC、IJK 及其所含相关库以共享库形式提供。本发行版的 LibVLC 使用固定上游基址及公开补丁重新构建，选择官方 `l` 许可配置，关闭 GPL contrib 并额外排除已核实主授权为 GPL 的插件。LibVLC 组合中的独立组件继续适用各自许可证及附加条款。

IJK 两种 ARM ABI 原生库保留上游 GSY SDK 制品字节，其 FFmpeg 构建均声明 `--disable-gpl` 与 `--disable-nonfree`。GSY 制品的 Apache 发布元数据和各原生库的 LGPL 许可分别适用于对应代码。

使用者保留依据相应 LGPL 许可证复制、研究、修改和再分发这些库的权利，以及为使用修改后的库和调试相关修改所需的替换、重新链接与逆向工程权利。这些权利依相应许可证优先适用。完整条款见本仓库附带的许可证原文。[LGPL 2.1 原文](LICENSES/LGPL-2.1.txt)、[LGPL 3.0 原文](LICENSES/LGPL-3.0.txt)、[GPL 3.0 基础条款](LICENSES/GPL-3.0.txt)

本版本第三方库的源码、构建资料、原始版权通知及制品对应关系在公众版仓库中增量维护，清单记录原生版本标识、上游提交和构建说明。Android 应用业务实现的授权范围由应用自身说明确定。[第三方源码与构建材料](https://github.com/heavenke/AuroraTV-Public/tree/main/third-party)

共享库替换、重新链接及 Android 自签安装的操作流程另附说明。[第三方共享库替换与重新打包](Library-replacement.md)

## 原生组件版本对应信息

| 制品部分 | 随包标识或上游对应信息 |
| --- | --- |
| LibVLC core | `4.0.0-dev-37538-gc84ef1eda4`，对应 VLC 提交 `c84ef1eda4f14f8b57a5b266b51c843cf51ed28b` |
| LibVLC JNI / Android 构建材料 | Android `libvlc-4.0.0-eap29` 标签所锁定的 JNI 提交 `a8d53a9151d7e4a9a5dfd0a5eb1cd92669afdc21` |
| 本发行版 LibVLC 派生 AAR | Android API 21，`arm64-v8a` 与 `armeabi-v7a`；当前主线AAR SHA-256为`bc3928df4b1bcf8314e1776d741d96556426037a5eb99d1e1a3080e065308b8e`，逐共享库指纹和补丁见同版本源码资料 |
| IJK ARM64 | `k0.8.8-43-g30eb9441`，对应维护提交 `30eb9441945da795079492041a791c121d2b8206`；FFmpeg 构建标识 4.1.6 |
| IJK ARMv7 | `k0.8.8-32-ge99d640e`，对应维护提交 `e99d640e5fe94c65132379307f92d7180bcde8e7`；FFmpeg 构建标识 `4.0--ijk0.8.8--20210205--001` |

以上原生标识用于定位对应材料，构建分支和外部依赖版本按第三方资料附件内的逐项映射说明确定。[VLC core 提交](https://github.com/videolan/vlc/tree/c84ef1eda4f14f8b57a5b266b51c843cf51ed28b)、[IJK ARM64 提交](https://github.com/CarGuo/ijkplayer/tree/30eb9441945da795079492041a791c121d2b8206)、[IJK ARMv7 提交](https://github.com/CarGuo/ijkplayer/tree/e99d640e5fe94c65132379307f92d7180bcde8e7)

## LibVLC 构建与功能差异

X-Team 在上述固定基址应用 Android 构建补丁和模块筛选，重新生成两种 ABI 的 `libvlc.so`、`libvlcjni.so`，并采用对应 NDK r28c 的 `libc++_shared.so`。Java `classes.jar`、Android Manifest 和 Android 资源保留 eap29 Maven 制品原字节。所用构建脚本、源码归档、补丁、工具链来源、实际配置和模块授权审计随同版本第三方资料提供。

2026-11-13本轮增量修改两种ABI的`libvlc.so`，其他JNI、运行库、Java及既有派生SDK资源字节保持。补丁路径为`tools/patches/vlc-mediacodec-mtk-main10-profile-fallback.patch`，为MediaTek HEVC Main10的profile漏报增加可选候选检索轮次。原生开关默认关闭，极光视界在自动与硬解模式启用；优先采用原有声明匹配候选，随后才允许对应MTK候选进入真实codec配置，配置及输出失败沿用原回退处理。该修改继续受对应VLC文件原有许可证约束。

最终每个 ABI 注册 305 个静态插件。筛选移除了 dummy / rc 命令行接口、file_logger / syslog 日志插件、Lua、stream_out_cycle / stream_out_rtp 流输出、hqdn3d 降噪、rotate 任意角度旋转及 deinterlace 软件去隔行插件族，包含对应架构优化实现。原 AAR 的 Lua 封面、网页播放列表脚本与 3D HRTF `.sofa` 数据一起移除。

本轮双ABI重新执行模块源授权审计，各为305个注册插件，GPL主授权模块源命中0；各自报告与当前AAR摘要清单保留对应关系。封装工具同时检查ELF节表边界以拒绝截断文件，原生播放能力由APP集成回归另行记录。

实际注册表包含 TS、MKV、avcodec、MediaCodec、Android 显示、libass 和 FreeType 模块，字幕字体依赖设备系统字体及对应字体渲染组件。RTSP 等能力沿用所选 `l` 配置下的实际模块集合。模块存在性、原生播放回归及用户实际观看效果分别记录于构建资料和测试结果。

LibVLC 构建所用源码归档中的版权、许可证和作者通知另行汇编保留，每节列出归档名、原始路径及 SHA-256。汇编也保留源码包内可选组件、测试文件和宿主工具的通知；实际链接范围按同版本构建配置、链接记录及模块清单核对，各通知分别适用于其覆盖文件。[VLC 组件原始通知](LICENSES/VLC-contrib-NOTICES.txt)

## FreeType 致谢

本软件部分基于 FreeType Team 的工作。FreeType 的原始版权、许可条件与免责条款保存在组件通知汇编的 `freetype-2.13.1/docs/FTL.TXT` 中。[FreeType Project](https://www.freetype.org/)、[组件通知与 FTL 原文](LICENSES/VLC-contrib-NOTICES.txt)

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
- [GNU Lesser General Public License 3.0](LICENSES/LGPL-3.0.txt)
- [GNU General Public License 3.0](LICENSES/GPL-3.0.txt)
- [CC0 1.0 Universal](LICENSES/CC0-1.0.txt)
- [LLVM libc++ 许可证与 LLVM exception](LICENSES/LLVM-libcxx-LICENSE.txt)
- [LLVM libc++abi 许可证与 LLVM exception](LICENSES/LLVM-libcxxabi-LICENSE.txt)
- [LLVM libunwind 许可证与 LLVM exception](LICENSES/LLVM-libunwind-LICENSE.txt)
- [VLC 所用源码组件的版权与许可通知](LICENSES/VLC-contrib-NOTICES.txt)
- [ZXing 上游 NOTICE](LICENSES/ZXing-NOTICE.txt)
- [dexlib2 上游版权与许可通知](LICENSES/dexlib2-NOTICE.txt)
- [原文来源与文件校验值](LICENSES/SOURCES.md)

源码包中的独立组件继续保留各自许可证、版权及 NOTICE 文件。媒体来源插件与其发布者的代码另按对应作者许可使用；用户自行配置后取得的 JAR 由对应来源提供。rtp2httpd 作为独立 HTTP TS 服务进行互操作，相关项目按其自己的发行许可提供。[rtp2httpd](https://github.com/stackia/rtp2httpd)

各第三方软件的担保和责任条款按所附原文执行。
