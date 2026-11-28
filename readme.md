![极光视界 Aurora TV](docs/brand/banner.png)

# 极光视界 · Aurora TV

<p align="center">
  <a href="https://aurora-tv.com/"><strong>🌌 极光视界官网正式上线 · aurora-tv.com</strong></a><br>
  界面预览 · 使用指南 · 应用下载
</p>

基于原生 Android TV 开发的聚合式媒体播放平台, 采用Material Design 3风格视觉语言, 兼容 Android TV、机顶盒、手机、平板、车机, 支持遥控器、PC键盘与触屏操作。

# 设备要求

Android 5.0+，ARM64/ARM32 架构。

[下载最新安装包](https://github.com/heavenke/AuroraTV-Public/releases/latest/download/AuroraTV-v1.0.12.261128-release-signed.apk) · [更新日志](CHANGELOG.md)

## 配置与使用教程

[📖 图文配置与使用教程（GitHub Wiki）](https://github.com/heavenke/AuroraTV-Public/wiki) · [官网使用指南](https://aurora-tv.com/guide/getting-started)

从安装和首次向导开始，了解直播、节目单、台标、点播来源、分类排序、播放操作与日志导出。

## 功能

- **媒体聚合**　接入影视服务器、挂载网盘、聚合存储(OpenList)，支持多站点、二级媒体库、搜索、筛选及自定义首页分类，支持后台刮削、自带 NFO 和封面海报补全。
- **直播观看**　M3U/TXT 混合聚合，收藏、数字选台、多线路切换，EPG节目单支持 XMLTV、DIYP、超级直播格式与台标模板。
- **快速换台**　专项适配 rtp2httpd HTTP TS/FCC，保留完整地址参数，协调输入连接和画面交接。效果依服务端 FCC 能力、网络与终端解码性能而定。[rtp2httpd](https://github.com/stackia/rtp2httpd)
- **统一播放**　统一播放直播、回放与点播，提供自动／硬解／软解、双渲染、续播、音轨、字幕、倍速与原始比例，按来源提供的历史能力支持回放与时移。
- **杜比视界**　支持杜比视界的设备可播放杜比视界片源。
- **杜比全景声**　自动识别并优先选择 Atmos 音轨。
- **色彩映射**　支持点播 HDR10／HLG 与杜比视界转 SDR，流畅度受设备性能影响。
- **便捷操作**　扫码或本机 WebUI 配置，手机竖屏浏览、横屏播放，支持触控手势设置、清晰焦点与操作引导，支持点播长按临时 2× 快进(可在点播设置中调整倍率)。
- **持续更新**　支持在线更新，长期维护。

## 已支持列表

- **影视服务器:**　飞牛影视、Emby、Jellyfin
- **网盘挂载:**　夸克网盘、百度网盘、115网盘、天翼云盘、迅雷网盘、光鸭云盘
- **兼容点播源:**　TVBox
- **其它类型:**　OpenList、WebDav、SMB共享

## 界面

截图来自早期版本；播放设置以当前使用指南为准。

| 电视 | 平板 |
| --- | --- |
| <img src="images/tv-live.png" alt="TV端直播界面" width="600"> | <img src="images/tablet-live.png" alt="触屏端直播界面" width="600"> |
| <img src="images/tv-library.png" alt="TV端媒体库界面" width="600"> | <img src="images/tablet-library.png" alt="触屏端媒体库界面" width="600"> |

| 手机直播页 | 手机媒体库 |
| --- | --- |
| <img src="images/phone-live.jpg" alt="手机端直播界面" width="600"> | <img src="https://raw.githubusercontent.com/heavenke/AuroraTV-Public/fcdbe4f00787a9cec430e3f7efe25bf8f9db35f6/images/phone-library.jpg" alt="手机端媒体库界面" width="600"> |

## 致谢

- 播放器内核使用了[MPV](https://github.com/mpv-player/mpv) 开源内核。
- 部份网盘接口使用了[OpenList](https://github.com/OpenListTeam/OpenList) 驱动。
- TVBox 爬虫采用了[takagen99](https://github.com/takagen99/Box) 大佬维护的TVBox仓库中部份代码。

# 关于

极光视界主体架构是自行设计, 部份实现由AI辅助开发。

极光视界只提供解码播放功能, 媒体内容由用户自行配置的来源提供。

本应用主体版权归「极光视界」所有并保留全部权利，未经授权不得进行逆向破解及收费分发。

第三方组件适用各自许可证，相关修改、调试与库替换权利见下方许可说明。

反馈时请附设备、Android 版本、解码／渲染方式及复现步骤，最好能提供调试日志。

[第三方组件说明](THIRD_PARTY_NOTICES.md) · [第三方源码与替换材料](third-party/) · [库替换说明](Library-replacement.md)

Copyright © 2026 AuroraTV All Rights Reserved.
