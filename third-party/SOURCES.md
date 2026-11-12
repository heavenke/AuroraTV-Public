# 第三方源码与SDK重构材料

本目录提供公众版使用的第三方源码、授权通知、配置与必要SDK补丁。极光视界应用主体及品牌版权归其权利人所有，主体按闭源方式分发；各第三方文件继续适用其原有许可证。

## 目录与制品对应

- `sources/`直接展开固定版本的VLC、LibVLC JNI、两版IJK、对应FFmpeg、OpenSSL、libyuv、SoundTouch、DVD组件、LIVE555和Java绑定源码，供Git按文件增量维护。原始归档摘要及每个展开文件的摘要见`source-tree-manifest.json`。
- `current/`记录当前双ARM LibVLC派生SDK的逐文件摘要与模块授权审计。当前AAR SHA-256为`bc3928df4b1bcf8314e1776d741d96556426037a5eb99d1e1a3080e065308b8e`。
- `tools/`保留SDK提取、补丁准备、构建、审计与封装工具。`tools/patches/vlc-mediacodec-mtk-main10-profile-fallback.patch`为当前MTK Main10候选选择补丁，默认关闭原生开关，由APP在自动与硬解模式启用。
- `materials/baseline-1112/`保留既有第三方构建配置、组件授权通知、上游来源与历史审计材料。旧SDK摘要对应原历史制品，当前SDK使用`current/`清单。
- `archive-index.json`记录全部归档的固定获取位置、原始大小与SHA-256，contrib归档同时保留对应固定VLC取源规则及可用的SHA-512。大归档下载到Git忽略的`.cache/`。

本轮SDK相对上一双ARM派生版本更新两个ABI的`libvlc.so`，JNI、C++运行库、Java、Manifest与既有资源沿用先前字节。两ABI各注册305个静态插件，GPL主授权模块源命中0，审计范围与组件集合以`current/audit-*`及各自许可证为准。

## 获取原始归档与重构建

使用Python 3.9及以上版本。默认获取核心归档，已缓存文件逐个校验后复用。

```sh
cd third-party
python3 tools/fetch_sources.py
```

`--all`同时获取contrib和NDK运行库源码。`--prepare-build`创建一个空的固定JNI/VLC构建树，并准备contrib源码缓存，随后复用原构建工具。

```sh
python3 tools/fetch_sources.py --prepare-build rebuild-source
export ANDROID_NDK=/path/to/android-ndk-r28c
export ANDROID_HOME=/path/to/android-sdk
bash tools/build_libvlc_lgpl.sh rebuild-source rebuild-output
```

Linux依赖、NDK版本、审计与封装参数见[LibVLC重构建说明](tools/build_libvlc_lgpl_README.md)。直接展开到Git的源码树保留原始内容；在Windows整理时，安全的文件链接会物化为对应文件，指向源码树外的开发链接仅记录元数据，原链接记录在源码树清单中。`--prepare-build`重新从校验后的原始归档提取，以恢复Linux构建所需的模式与链接元数据。

固定上游地址不可用时，获取脚本使用已公开的1112源码资料补充副本，校验整个资料包后仅取索引指定的原始归档，并再次校验归档SHA-256。该既有补充资料的SHA-256为`73baaa44cd9079f9b5bbe1bf2b5afb3715308f71120ce308735d5d323c21caa2`。[既有1112第三方源码资料](https://github.com/heavenke/AuroraTV-Public/releases/download/v1.0.0.1112/AuroraTV-ThirdParty-Sources-v1.0.0.1112.zip)

后续版本继续在本目录维护新增补丁、源码与当前清单，并使用Git记录差异。
