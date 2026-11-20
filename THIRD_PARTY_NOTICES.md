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
| Guava Android | `com.google.guava:guava:33.3.1-android`，媒体组件共用的集合与基础工具 | Apache-2.0，[固定版本源码](https://github.com/google/guava/tree/v33.3.1/android) |
| JSR-305 注解 | `com.google.code.findbugs:jsr305:3.0.2`，共用库的注解依赖 | Apache-2.0，[固定来源制品及源码](https://repo.maven.apache.org/maven2/com/google/code/findbugs/jsr305/3.0.2/) |
| core-js 与 Babel 生成的运行时辅助代码 | 内置配置页的 ES5 与 Promise、集合兼容，支持 Android 5.0 WebView | MIT，[原始版权与许可](LICENSES/Config-web-runtime-LICENSE.txt) |
| Android NDK C++ 运行库 | NDK r28c `28.2.13676358` 的双 ARM `libc++_shared.so`，Clang 19.0.1、LLVM 固定提交 `97a699bf4812a18fb657c2779f5296a4ab2694d2` | libc++、libc++abi、libunwind 的 Apache-2.0 WITH LLVM-exception 及保留的历史条款，[Android LLVM 对应源码](https://android.googlesource.com/toolchain/llvm-project/+/97a699bf4812a18fb657c2779f5296a4ab2694d2/) |

AndroidX、Kotlin 和其它传递依赖随解析后的运行时一起使用。各项目内独立文件及所含依赖的授权声明继续有效，详细原始通知、源码与构建资料按照本版本的第三方资料清单查阅。

## Python 插件运行时与依赖

Python 来源使用 Chaquopy 15.0.1 与 Android CPython target 3.11.6-0，保留双 ARM 和 Android 5.0 支持。下列依赖随 APK 提供，原始许可证按本次实际打包版本保存。完整原文、摘要、官方源码与 target 构建配方统一列在来源清单中。[Python 许可证与源码清单](LICENSES/Python-SOURCES.md)

| 组件 | 实际版本 | 许可与随包原文 |
| --- | --- | --- |
| Chaquopy Java / JNI 运行时 | 15.0.1 | MIT，[原文](LICENSES/Chaquopy-15.0.1-LICENSE.txt) |
| Chaquopy bootstrap 中的 pyelftools / Construct | 0.26 / 2.06 | Public domain / MIT，[pyelftools 原文](LICENSES/Chaquopy-pyelftools-0.26-LICENSE.txt)、[Construct 原文](LICENSES/Chaquopy-construct-2.06-LICENSE.txt) |
| CPython 解释器与标准库 | 3.11.6，Android target 3.11.6-0 | PSF 及各独立组件原声明，[历史许可全文](LICENSES/CPython-3.11.6-LICENSE.txt)、[标准库完整附带通知](LICENSES/CPython-3.11.6-stdlib-NOTICES.txt) |
| requests | 2.32.3 | Apache-2.0，[原文](LICENSES/requests-2.32.3-LICENSE.txt) |
| PyCryptodome | 3.9.4 | Public domain、BSD-2-Clause 及所含算法声明，[完整原文](LICENSES/pycryptodome-3.9.4-LICENSE.txt) |
| idna | 3.20 | BSD-3-Clause，[原文](LICENSES/idna-3.20-LICENSE.txt) |
| urllib3 | 2.8.0 | MIT，[原文](LICENSES/urllib3-2.8.0-LICENSE.txt) |
| charset-normalizer | 3.5.2 | MIT，[原文](LICENSES/charset_normalizer-3.5.2-LICENSE.txt) |
| certifi / Mozilla CA 集合 | 2026.10.23 | MPL-2.0，[原始通知](LICENSES/certifi-2026.10.23-LICENSE.txt)、[MPL-2.0 全文](LICENSES/MPL-2.0.txt) |
| CPython target 的 OpenSSL、SQLite、libffi、bzip2、liblzma | 3.0.5、3.39.2、3.4.4、1.0.8、5.4.5 | 各自保留 Apache-2.0、public-domain、MIT/BSD 等原声明，详见 [完整原文及固定来源](LICENSES/Python-SOURCES.md) |

certifi 对应的 MPL 源码从官方同版本发布页获取，覆盖文件保持上游内容。[certifi 2026.10.23 官方源码发布](https://pypi.org/project/certifi/2026.10.23/#files)、[certifi 官方仓库](https://github.com/certifi/python-certifi)

Chaquopy 对 CPython 的 Android target 适配补丁与构建配方保留在固定上游提交中。Python 脚本的来源、作者及许可由相应配置发布者提供，用户私有影视脚本未随 APK 分发。[Chaquopy 固定源码及 Android 构建配方](https://github.com/chaquo/chaquopy/tree/826262dee50f7abfd27edc9072996ddfe2ffbab2)

## LGPL 组件与用户权利

MPV 0.42.0 与 FFmpeg 9.0.2、libplacebo 7.387.0、libass 0.17.5、mbedTLS 3.6.7、FreeType 2.15.0、FriBidi 1.0.17、HarfBuzz 15.0.0、libunibreak 8.0、libxml2 2.15.4、fontconfig 2.18.3、dav1d 1.5.3 组成独立共享库 `libaurora_mpv_core.so`。MPV 以 `gpl=false` 构建，FFmpeg 关闭 GPL/nonfree 并启用 version3；该核心按 LGPL-3.0-or-later 提供，内部依赖同时保留其各自条款。MPV C API 和 Android 环境入口与应用薄 JNI 动态链接，允许用户修改、重新链接及替换核心。

原始许可证和版权声明见 [MPV](third-party/mpv/licenses/mpv/Copyright)、[FFmpeg](third-party/mpv/licenses/ffmpeg/LICENSE.md)、[libplacebo](third-party/mpv/licenses/libplacebo/LICENSE)、[libass](third-party/mpv/licenses/libass/COPYING)、[mbedTLS](third-party/mpv/licenses/mbedtls/LICENSE)、[FreeType](third-party/mpv/licenses/freetype/docs/FTL.TXT)、[FriBidi](third-party/mpv/licenses/fribidi/COPYING)、[HarfBuzz](third-party/mpv/licenses/harfbuzz/COPYING)、[libunibreak](third-party/mpv/licenses/unibreak/LICENCE)、[libxml2](third-party/mpv/licenses/libxml2/Copyright)、[fontconfig](third-party/mpv/licenses/fontconfig/COPYING)、[dav1d](third-party/mpv/licenses/dav1d/COPYING)。构建时使用的 GLAD、Jinja、MarkupSafe、fast_float 的原始通知与 NDK 静态运行时通知也保留在 `MPV/` 下。固定源码归档、完整构建配方和两 ABI 对应清单随该版 APK 的第三方资料附件提供。

使用者保留依据相应 LGPL 许可证复制、研究、修改和再分发这些库的权利，以及为使用修改后的库和调试相关修改所需的替换、重新链接与逆向工程权利。这些权利依相应许可证优先适用。完整条款见本仓库附带的许可证原文。[LGPL 2.1 原文](LICENSES/LGPL-2.1.txt)、[LGPL 3.0 原文](LICENSES/LGPL-3.0.txt)、[GPL 3.0 基础条款](LICENSES/GPL-3.0.txt)

本版本第三方库的源码、构建资料、原始版权通知及制品对应关系在公众版仓库中增量维护，清单记录原生版本标识、上游提交和构建说明。Android 应用业务实现的授权范围由应用自身说明确定。[第三方源码与构建材料](https://github.com/heavenke/AuroraTV-Public/tree/main/third-party)

共享库替换、重新链接及 Android 自签安装的操作流程另附说明。[第三方共享库替换与重新打包](Library-replacement.md)

## FreeType 致谢

本软件部分基于 FreeType Team 的工作。[FreeType 许可原文](third-party/mpv/licenses/freetype/docs/FTL.TXT)

## 许可证原文与附带通知

配置向导中的来源标识采用对应品牌轮廓并调整为极光配色。标识来源、修改及许可见随包的 Source-brand-icons-NOTICE.txt，Jellyfin 和 TVBox 图形保留各自的许可文本与可编辑资源。

- [Apache License 2.0](LICENSES/Apache-2.0.txt)
- [GNU Lesser General Public License 2.1](LICENSES/LGPL-2.1.txt)
- [GNU Lesser General Public License 3.0](LICENSES/LGPL-3.0.txt)
- [GNU General Public License 3.0](LICENSES/GPL-3.0.txt)
- [CC0 1.0 Universal](LICENSES/CC0-1.0.txt)
- [LLVM libc++ 许可证与 LLVM exception](LICENSES/LLVM-libcxx-LICENSE.txt)
- [LLVM libc++abi 许可证与 LLVM exception](LICENSES/LLVM-libcxxabi-LICENSE.txt)
- [LLVM libunwind 许可证与 LLVM exception](LICENSES/LLVM-libunwind-LICENSE.txt)
- [ZXing 上游 NOTICE](LICENSES/ZXing-NOTICE.txt)
- [原文来源与文件校验值](LICENSES/SOURCES.md)

源码包中的独立组件继续保留各自许可证、版权及 NOTICE 文件。媒体来源插件与其发布者的代码另按对应作者许可使用；用户自行配置后取得的 JAR 由对应来源提供。rtp2httpd 作为独立 HTTP TS 服务进行互操作，相关项目按其自己的发行许可提供。[rtp2httpd](https://github.com/stackia/rtp2httpd)

各第三方软件的担保和责任条款按所附原文执行。

## 挂载媒体库与刮削

SMB 挂载使用 SMBJ、ASN One、MBassador、SLF4J 和 Bouncy Castle。网页元数据解析使用 jsoup。相关许可与通知见 [LICENSES](LICENSES)。挂载媒体库的在线资料可来自 IMDb、豆瓣、TMDB、Wikidata 和中文维基百科。Aurora TV 使用 TMDB 资料，未经 TMDB 认证或背书。
