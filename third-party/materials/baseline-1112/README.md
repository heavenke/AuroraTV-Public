# 第三方播放器源码与构建材料

本资料为极光视界 v1.0.0.1112 所用公开上游播放器依赖整理，包含固定版本源码、发布者补丁、Maven源码制品、构建规则与校验记录。组件版权和许可沿用各源码文件及其COPYING、LICENSE和NOTICE。

## 本次 LibVLC 源码构建

发布准备采用同一 JNI 和 VLC 固定基址重新构建的双 ARM SDK。构建选择官方 license l，额外排除已核实主授权为 GPL 的插件及 deinterlace 优化插件族，同时移除原 Maven AAR 的 Lua 和 HRTF assets。最终 native 文件及其 SHA-256 以 rebuilt-libvlc 内的实际构建记录为准。

rebuilt-libvlc 收录本次构建的 contrib 下载源码、两 ABI 的配置、完整 VLC 应用补丁、修改后的构建脚本、工具链来源、宿主适配源码、实际静态模块授权审计及重建工具。contrib-archive-index.json 对下载归档逐项记录大小、SHA-256、SHA-512 与固定源码树的取源规则。工具链采用 NDK r28c，Clang 19.0.1；libcxx、libcxxabi、libunwind、runtimes 和 cmake 的 Android 官方固定源码另列于 toolchain/sources。

递归授权审计基于真实生成的 SOURCES、LIBADD 和最终静态模块注册表，额外追踪内部 helper 库与可解析的本地头文件。主授权语句与文件末尾的 received-copy 文字分别处理。生成的 config.h、语法分析器及 protobuf 源码等边界保留在审计记录中。

原 Maven 制品的版本识别和 hash 留作基址核验材料。下方原 Maven LibVLC 行以及根目录的 binary-evidence.json、apk-native-validation.json 不代替本次重编 native 的指纹。

### 从归档开始重建

Linux 依赖、固定归档校验、双 ABI 编译、模块审计和 AAR 封装步骤位于 rebuilt-libvlc/tools/build_libvlc_lgpl_README.md。在 rebuilt-libvlc 目录执行其中命令，将 archives 参数指向资料根目录的 archives。展开工具核验原归档 SHA-256，并创建逐文件清单供后续准备步骤校验。

可将 rebuilt-libvlc/contrib-source-archives 中的文件复制到展开后的 vlc/contrib/tarballs，复用本次真实下载源码。VLC 规则中的 SHA-512 或固定 git archive 提交会继续核对这些缓存。Android SDK、NDK、Linux 构建工具及 Python 构建依赖按构建说明准备。

本次在 WSL1 上运行的宿主适配源文件保存在 build-evidence 与 host-overlay。其记录中的开发机缓存路径可按实际目录调整。最终两 ABI 的官方配置 l 构建及额外黑名单重链日志保留在 build-evidence/logs，早期 arm 构建的在途脚本偏移错误也保留，最终成功结果对应 relink-arm-lgpl.log。归档展开与补丁准备通过 smoke 校验，完整源码重建以本次保留的实际构建记录为依据。

contrib-notices 保存从下载源码提取的版权、许可、NOTICE 和作者原文，source-index.json 记录各原文及原归档摘要。集合同时保留构建工具、可选模块及源码测试内容，二进制的启用组成可结合最终模块注册表、链接配置与 pkg-config 记录查阅。

## 核验关系

| 制品 | 实际二进制标识 | 固定源码与证据 |
| --- | --- | --- |
| org.videolan.android:libvlc-all:4.0.0-eap29 | 双ARM的VLC版本为4.0.0-dev-37538-gc84ef1eda4 | vlc-android的libvlc-4.0.0-eap29发布标签锁定libvlcjni a8d53a9151d7e4a9a5dfd0a5eb1cd92669afdc21；其get-vlc.sh锁定VLC c84ef1eda4f14f8b57a5b266b51c843cf51ed28b，与native标识一致 |
| gsyvideoplayer-arm64:11.3.0 | IJK k0.8.8-43-g30eb9441，FFmpeg ff4.1.6，OpenSSL 1.1.1w | IJK基址30eb9441945da795079492041a791c121d2b8206；GSY v11.3.0所含三份arm64预编译库与Maven AAR逐字节一致；CarGuo FFmpeg ff4.1.6指向700795a85fd23f2b70929b942cab1d3409ac53ba |
| gsyvideoplayer-armv7a:11.3.0 | IJK k0.8.8-32-ge99d640e，FFmpeg ff4.0--ijk0.8.8--20210205--001，OpenSSL 1.0.2q | IJK基址e99d640e5fe94c65132379307f92d7180bcde8e7；其init脚本锁定Bilibili FFmpeg f886615aaba147aeaeb69bc199766cf52f980713。GSY v11.3.0三份armv7库经NDK23 llvm-strip --strip-unneeded后与Maven AAR逐字节一致，全部PT_LOAD加载段也一致 |

LibVLC Java源码来自同一Maven版本的sources.jar，GSY IJK Java源码来自gsyijkjava 1.0.0的sources.jar。坐标、来源URL、文件大小和SHA256记录在source-manifest.json。

## 材料结构

- archives保存libvlcjni、VLC、两个IJK基址、两种FFmpeg维护fork、OpenSSL 1.0.2q/1.1.1w、IJK脚本所锁定的libyuv和SoundTouch源码。
- VLC的libdvdread 7.0.1、libdvdnav 7.0.0、libbluray 1.4.0、FFmpeg 8.1和LIVE555 2022.07.14发布源码也已收录，每份均通过该VLC提交contrib规则中的SHA512校验。
- build-materials保存固定发布标签的GSY 16K/NDK补丁、构建文档及VideoLAN构建/CI脚本。
- java-sources保存两个精确Maven版本的Java源码制品。
- vlc-contrib-source-index.json整理固定VLC提交下131组上游contrib取源规则及校验和，完整补丁位于VLC源码压缩包的contrib/src中。
- binary-evidence.json、native-tag-validation.json及apk-native-validation.json记录native版本、文件hash、运行加载段和原始Maven制品对照。
- upstream-metadata保留固定提交、标签、源码树及构建说明获取记录。
- SHA256SUMS可用于验证本目录文件。

## 仍待校对的构建边界

ARM64 IJK的二进制基址为30eb9441，其原始init-android.sh仍引用FFmpeg 4.0维护标签，而发布二进制使用ff4.1.6和OpenSSL 1.1.1w。包内已收录实际版本对应的维护fork源码及GSY发布标签公开补丁，发布者最终本地工作树和全部构建参数的完整重建验证仍待完成。

根目录 VLC contrib 索引描述整个固定源码树。原 Maven 预编译 contrib 的完整发布工作树仍由上游发布过程决定。本次重新构建另外保留实际配置、下载源码及构建证据，详见 rebuilt-libvlc。构建脚本保留 g、l、a 三种许可模式和发布 CI 原文，各组成模块的许可范围取自实际源码与制品。

本资料的版本识别与校验记录用于说明来源对应关系，二进制重建结果以各上游公开构建方法及实际验证记录为准。
