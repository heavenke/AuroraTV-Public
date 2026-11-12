![极光视界 Aurora TV](docs/brand/banner.png)

# 极光视界 · Aurora TV

将直播与家庭媒体库汇聚到同一首页，为 Android 电视、盒子、平板和手机分别适配遥控、键盘与触屏布局。支持 Android 5.0+，提供 ARM64 与 ARM32 安装包架构。

[下载最新安装包](https://github.com/heavenke/AuroraTV-Public/releases/latest/download/release.apk) · [更新日志](CHANGELOG.md)

## 功能

- **媒体聚合**　接入飞牛影视、Emby、Jellyfin 和 TVBox JSON/JAR，支持多站点、二级媒体库、搜索、筛选及自定义首页分类。
- **直播观看**　M3U/TXT 混合聚合，收藏、数字选台、多线路切换，直播分类可改名，节目单支持 XMLTV、DIYP、超级直播格式与台标模板。
- **快速换台**　专项适配 rtp2httpd HTTP TS/FCC，保留完整地址参数，协调输入连接和画面交接。效果依服务端 FCC 能力、网络与终端解码性能而定。[rtp2httpd](https://github.com/stackia/rtp2httpd)
- **统一播放**　系统、VLC、IjkPlayer 三引擎，提供续播、音轨、字幕、倍速与原始比例，按来源提供的历史能力支持回放与时移。
- **便捷操作**　扫码或本机 WebView 配置，手机竖屏浏览、横屏播放，支持触控手势设置、清晰焦点与操作引导。
- **持续更新**　展示公告与更新日志，支持在线更新，安装前校验 SHA-256 和应用签名。

## 界面

| 电视 | 平板 |
| --- | --- |
| ![电视直播](images/tv-live.png) | ![平板直播](images/tablet-live.png) |
| ![电视媒体库](images/tv-library.png) | ![平板媒体库](images/tablet-library.png) |

本仓库用于闭源公众版介绍与发布。应用主体版权归 X-Team 所有并保留全部权利，未经授权不得公开主体源码。媒体内容由用户自行配置的来源提供。反馈时请附设备、Android 版本、引擎及复现步骤，并移除私有地址与凭据。

[第三方组件说明](THIRD_PARTY_NOTICES.md) · [第三方源码与替换材料](third-party/) · [库替换说明](Library-replacement.md)

Copyright © 2026 X-Team All Rights Reserved.
