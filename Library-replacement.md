# 第三方共享库替换与重新打包

极光视界以 Android 共享库方式使用 LibVLC、IJK 等组件。使用者可依对应许可证修改这些库、重新链接或替换共享库，并进行调试这些修改所需的逆向工程。应用主体采用闭源分发，第三方组件的权利按其许可证保留。[第三方软件通知](THIRD_PARTY_NOTICES.md)

## 准备对应版本

下载同一 Release 中的正式 APK、第三方源码与构建资料附件，核对附件清单及 SHA-256。资料中的上游提交、补丁、工具链、配置和组件许可证用于重建对应共享库。各组件及传递依赖分别适用其原始许可。[发布与附件](https://github.com/heavenke/AuroraTV-Public/releases)

正式 APK 提供已经编译的 `classes*.dex`、资源、Manifest 和共享库。替换共享库时可复用其中的应用对象代码，保留 Java/JNI 接口和原有库加载名称。按设备 ABI 准备完整兼容的共享库集合，分别放入 `lib/arm64-v8a/` 或 `lib/armeabi-v7a/`。静态链接到共享库的组件修改后，需要重新链接包含它的共享库；修改引入额外共享库依赖时，一并放入对应 ABI 目录。

本版 LibVLC 使用 NDK r28c 重建，替换时应一并核对 `libvlc.so`、`libvlcjni.so` 与 `libc++_shared.so` 的兼容关系。实际工具链、模块配置和每个共享库的 SHA-256 见同版本资料清单。

## 替换与签名

在正式 APK 的副本中替换相应 `lib/<ABI>/*.so`，保持其余应用对象代码和资源。重新生成 ZIP 格式的 APK，并去掉旧的 JAR 签名文件及 APK Signing Block。保留第三方许可、NOTICE 和其它应用文件。可使用下面的 Python 示例从原 APK 创建替换后的副本，`replacement` 目录应包含上述 `lib/<ABI>/` 层级。

```python
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED

original = Path("official.apk")
replacement = Path("replacement")
output = Path("repacked.apk")
files = {p.relative_to(replacement).as_posix(): p
         for p in replacement.rglob("*.so")}
allowed = ("lib/arm64-v8a/", "lib/armeabi-v7a/")
if not files or any(not name.startswith(allowed) for name in files):
    raise ValueError("替换文件必须位于支持的 lib/ABI 目录")

with ZipFile(original) as source, ZipFile(output, "w") as target:
    names = source.namelist()
    if len(names) != len(set(names)):
        raise ValueError("原 APK 包含重复条目")
    for entry in source.infolist():
        name = entry.filename
        upper = name.upper()
        signature = upper.startswith("META-INF/") and (
            upper == "META-INF/MANIFEST.MF"
            or upper.endswith((".SF", ".RSA", ".DSA", ".EC"))
        )
        if signature:
            continue
        data = files[name].read_bytes() if name in files else source.read(entry)
        target.writestr(entry, data)
    for name in files.keys() - set(names):
        target.writestr(name, files[name].read_bytes(), compress_type=ZIP_STORED)
```

使用 Android SDK Build Tools 对齐后，以自己的签名密钥签名并验证。下面的文件名为示例，`personal.jks` 为使用者自行创建并保存的密钥库，签名工具会交互读取密码。发行者的私有签名密钥由发行者保管。[Android 签名说明](https://developer.android.com/studio/publish/app-signing)

```text
zipalign -P 16 -f 4 repacked.apk aligned.apk
apksigner sign --ks personal.jks --out personal.apk aligned.apk
apksigner verify --verbose personal.apk
zipalign -c -P 16 4 personal.apk
```

`zipalign` 应在 `apksigner` 签名前执行，签名后修改文件会使签名失效。APK 对齐与 ELF 自身的页面兼容分别处理，重建共享库时还需采用适合目标设备的工具链配置。[zipalign](https://developer.android.com/tools/zipalign)、[apksigner](https://developer.android.com/tools/apksigner)

## 安装与后续更新

Android 按包名及签名身份校验覆盖安装。自签 APK 与正式发行版的签名身份不同，首次测试可使用独立设备，或在自行备份、迁移配置后卸载原版再安装。后续保持自己的签名密钥，使用更高版本代码的兼容 APK进行覆盖安装。[Android 应用签名与升级](https://developer.android.com/studio/publish/app-signing#considerations)

极光视界在线更新会验证内置公钥签名的更新信息、下载文件 SHA-256、包名、版本代码及安装包签名。自行替换库后的 APK 字节与官方发布校验值不同，自签版也具有不同的安装签名。用户可下载新的正式 APK 和对应源码资料，重新应用自己的共享库修改、以同一把个人密钥签名，通过系统安装器更新自签版本。遇到必须更新的版本要求时，也可采用这一流程安装对应新版本，继续使用修改后的库。

本说明保留相应 LGPL 允许的修改、替换、重新链接和调试权利。具体条款见随包原文及各组件通知。[LGPL 2.1](LICENSES/LGPL-2.1.txt)、[LGPL 3.0](LICENSES/LGPL-3.0.txt)、[GPL 3.0](LICENSES/GPL-3.0.txt)
