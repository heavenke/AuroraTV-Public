# LibVLC eap29 双 ARM 重构建

本构建固定使用 libvlcjni `a8d53a9151d7e4a9a5dfd0a5eb1cd92669afdc21` 与 VLC `c84ef1eda4f14f8b57a5b266b51c843cf51ed28b`，官方 `--license l` 配置，Android API 21，NDK r28c `28.2.13676358`。Java `classes.jar`、资源与 Manifest 保留原 Maven eap29 内容。

2026-11-13当前主线派生SDK为`app/libs/libvlc-all-4.0.0-eap29-aurora-lgpl.aar`，SHA-256为`bc3928df4b1bcf8314e1776d741d96556426037a5eb99d1e1a3080e065308b8e`。逐文件指纹与本轮源码补丁记录在[AAR清单](../current/libvlc-all-4.0.0-eap29-aurora-lgpl.manifest.json)。本轮相对上一双ARM派生SDK仅更新两个ABI的`libvlc.so`，其余JNI、C++运行库、Java、Manifest与资源沿用该派生SDK的既有字节。历史离线重构记录中的旧摘要继续对应当时制品。

## Linux 依赖

使用 JDK 17、Python 3、Linux Android SDK 与 NDK。编译依赖如下。Android SDK 的原生构建步骤不调用 SDK 中的 Windows 可执行文件。

```sh
apt-get install automake ant autopoint cmake build-essential libtool-bin patch pkg-config \
  protobuf-compiler ragel subversion unzip git flex python-is-python3 wget curl gettext \
  bison nasm yasm gperf texinfo help2man autoconf libtool python3-setuptools python3-pip python3-venv
```

官方 extras/tools 引导会构建所需新版 Autoconf、CMake、Meson 和 Ninja。源码发布附件包含本次 contrib 下载归档及校验信息，可按附件中的源码目录说明复用缓存。Python venv 缺少 wheel 时可在其创建后执行 `python-venv/bin/pip install wheel==0.45.1`。

## 从发布附件展开

源码附件的 `archives/` 内包含两个固定归档。展开工具先验证其内置 SHA-256，再生成逐文件摘要清单。目标目录须为空。此路径完全支持无 `.git` 的归档树。

```sh
python3 tools/build_libvlc_lgpl_extract.py /path/to/source-bundle/archives /path/to/rebuild-source
export ANDROID_NDK=/path/to/android-ndk-r28c
export ANDROID_HOME=/path/to/android-sdk
bash tools/build_libvlc_lgpl.sh /path/to/rebuild-source /path/to/output
```

## 从固定 Git 提交开始

也可获取相同固定提交的两个工作树。JNI 根目录下 `vlc/` 必须指向上述 VLC 提交。构建脚本校验 VLC HEAD 与 JNI 的 `VLC_TESTED_HASH`，保留未提交的官方 Android 补丁及本项目补丁供审计。使用前应核对 JNI HEAD 或已发布归档的 SHA-256。

```sh
git clone https://code.videolan.org/videolan/libvlcjni.git /path/to/rebuild-source
git -C /path/to/rebuild-source checkout a8d53a9151d7e4a9a5dfd0a5eb1cd92669afdc21
git clone https://code.videolan.org/videolan/vlc.git /path/to/rebuild-source/vlc
git -C /path/to/rebuild-source/vlc checkout c84ef1eda4f14f8b57a5b266b51c843cf51ed28b
bash tools/build_libvlc_lgpl.sh /path/to/rebuild-source /path/to/output
```

## 构建差异

- 官方 JNI 自带六个 Android 补丁原样应用。
- 本项目增加[MediaTek HEVC Main10候选选择补丁](patches/vlc-mediacodec-mtk-main10-profile-fallback.patch)。原生开关`mediacodec-mtk-main10-profile-fallback`默认关闭，APP在AUTO与HARDWARE模式按播放项启用。首轮沿原规则检索声明匹配的候选，首轮未选中时才进入第二轮，允许`c2.mtk.`或`OMX.MTK.`的HEVC Main10候选通过不完整的profile声明继续接受实际configure/start/output检验，真实错误沿原失败与回退链处理。构建脚本在官方Android补丁后依次应用`tools/patches/*.patch`。
- ZVBI 通过官方 `--disable-v4l` 参数关闭 Android 无法提供的 Linux V4L 采集。Teletext 解码继续构建。
- 官方 `l` 配置关闭 GPL contrib 后，模块归并仍需排除主授权为 GPL 的 CLI、logger、Lua、部分流输出及视频滤镜。完整名称见 `build_libvlc_lgpl_prepare.py`。普通 TS、Matroska、字幕与 MediaCodec 模块保留，具体以两 ABI 的最终注册模块审计为准。
- 原 AAR 的 Lua 脚本与 HRTF SOFA 资源移除。原 AAR 没有字体资源。常规文字字幕使用新构建 libass、Freetype、Harfbuzz 与 Android 字体，需要设备验证 SRT、ASS 和 PGS 的实际效果。
- 本次 WSL1 无法直接加载 Google BOLT Clang。使用源码附件中的 host-overlay/readlink shim 经 Linux 动态加载器运行原始 Clang。编译器原始字节保持，shim 仅在 Linux 构建主机运行。普通 Linux 可直接使用原始 NDK。

## 审计与封装

源码附件提供主授权清单及递归 helper/header 交叉报告。将 `--inventory` 指向对应的 `vlc-module-source-license-inventory.json`。两 ABI 分别运行审计，检查最终注册模块与所需播放模块。

```sh
python3 tools/build_libvlc_lgpl_audit.py \
  --source /path/to/rebuild-source/vlc \
  --build /path/to/rebuild-source/vlc/build-android-aarch64-linux-android \
  --inventory /path/to/vlc-module-source-license-inventory.json --output /path/to/output/audit-arm64
python3 tools/build_libvlc_lgpl_audit.py \
  --source /path/to/rebuild-source/vlc \
  --build /path/to/rebuild-source/vlc/build-android-arm-linux-androideabi \
  --inventory /path/to/vlc-module-source-license-inventory.json --output /path/to/output/audit-arm
python3 tools/build_libvlc_lgpl_package.py \
  --original-aar /path/to/libvlc-all-4.0.0-eap29.aar \
  --native-root /path/to/output/native \
  --output /path/to/output/libvlc-all-4.0.0-eap29-aurora-lgpl.aar
```

封装工具校验 ABI、六个原生库以及 Java 字节保留，生成 AAR、逐文件摘要及差异说明。设备起播、轨道与硬解兼容性由 APP 集成阶段验证。发布附件中同时保留 LGPL/GPL 全文、源材料与替换重链接说明。

本轮封装新增ELF section table边界检查，提前拒绝截断原生库，相关封装回归5项通过。最终双ABI审计各注册305个插件，GPL主授权模块源命中均为0，TS、MKV、MediaCodec、avcodec、Android显示与字幕模块检查通过。本机审计证据为`artifacts/main10-native-audit-arm64.log`、`artifacts/main10-native-audit-arm.log`及各自目录中的`module-license-audit.json`。

