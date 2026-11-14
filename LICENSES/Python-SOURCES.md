# Python 运行时与依赖许可证来源

本文记录随 APK 的 Chaquopy 15.0.1、Android CPython target 3.11.6-0 与已解析 Python 依赖。许可证文件保留原始字节。pip 包原文直接提取自本次打包的 dist-info，未使用构建主机 pip/setuptools 的许可证代替目标包。

Chaquopy 固定源码提交为 `826262dee50f7abfd27edc9072996ddfe2ffbab2`。双 ARM target 的版本由 Gradle 缓存 `com.chaquo.python:target:3.11.6-0` 核对，OpenSSL 3.0.5 与 SQLite 3.39.2 同时由 target 头文件核对，其余静态支持库版本按同版官方构建脚本列出。

| 原文文件 | 原始来源 | SHA-256 |
| --- | --- | --- |
| [CPython-3.11.6-LICENSE.txt](CPython-3.11.6-LICENSE.txt) | https://raw.githubusercontent.com/python/cpython/v3.11.6/LICENSE | `3b2f81fe21d181c499c59a256c8e1968455d6689d269aa85373bfb6af41da3bf` |
| [CPython-3.11.6-stdlib-NOTICES.txt](CPython-3.11.6-stdlib-NOTICES.txt) | https://raw.githubusercontent.com/python/cpython/v3.11.6/Doc/license.rst | `a83492480132cb11e585a6486f581872d1717bbbb361633684d71577b6ecd031` |
| [Chaquopy-15.0.1-LICENSE.txt](Chaquopy-15.0.1-LICENSE.txt) | https://raw.githubusercontent.com/chaquo/chaquopy/15.0.1/LICENSE.txt | `338d9a4f0a43079c18d24e374443cc6f1065234668f488b4c559650eb7b60f17` |
| [MPL-2.0.txt](MPL-2.0.txt) | https://www.mozilla.org/media/MPL/2.0/index.txt | `3f3d9e0024b1921b067d6f7f88deb4a60cbe7a78e76c64e3f1d7fc3b779b9d04` |
| [OpenSSL-3.0.5-LICENSE.txt](OpenSSL-3.0.5-LICENSE.txt) | https://raw.githubusercontent.com/openssl/openssl/openssl-3.0.5/LICENSE.txt | `7d5450cb2d142651b8afa315b5f238efc805dad827d91ba367d8516bc9d49e7a` |
| [SQLite-3.39.2-LICENSE.txt](SQLite-3.39.2-LICENSE.txt) | https://raw.githubusercontent.com/sqlite/sqlite/version-3.39.2/LICENSE.md | `9c6479123f32a1ed50d9a0af203dfe8972e65035b0cdeef436b5f8d0924517fe` |
| [XZ-5.4.5-COPYING.GPLv2.txt](XZ-5.4.5-COPYING.GPLv2.txt) | https://raw.githubusercontent.com/tukaani-project/xz/v5.4.5/COPYING.GPLv2 | `8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643` |
| [XZ-5.4.5-COPYING.GPLv3.txt](XZ-5.4.5-COPYING.GPLv3.txt) | https://raw.githubusercontent.com/tukaani-project/xz/v5.4.5/COPYING.GPLv3 | `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986` |
| [XZ-5.4.5-COPYING.LGPLv2.1.txt](XZ-5.4.5-COPYING.LGPLv2.1.txt) | https://raw.githubusercontent.com/tukaani-project/xz/v5.4.5/COPYING.LGPLv2.1 | `dc626520dcd53a22f727af3ee42c770e56c97a64fe3adb063799d8ab032fe551` |
| [XZ-5.4.5-COPYING.txt](XZ-5.4.5-COPYING.txt) | https://raw.githubusercontent.com/tukaani-project/xz/v5.4.5/COPYING | `72d7ef9c98be319fd34ce88b45203b36d5936f9c49e82bf3198ffee5e0c7d87e` |
| [bzip2-1.0.8-LICENSE.txt](bzip2-1.0.8-LICENSE.txt) | https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz (bzip2-1.0.8/LICENSE) | `c6dbbf828498be844a89eaa3b84adbab3199e342eb5cb2ed2f0d4ba7ec0f38a3` |
| [certifi-2026.10.23-LICENSE.txt](certifi-2026.10.23-LICENSE.txt) | https://pypi.org/project/certifi/2026.10.23/#files (wheel licenses/LICENSE) | `e93716da6b9c0d5a4a1df60fe695b370f0695603d21f6f83f053e42cfc10caf7` |
| [charset_normalizer-3.5.2-LICENSE.txt](charset_normalizer-3.5.2-LICENSE.txt) | https://pypi.org/project/charset-normalizer/3.5.2/#files (wheel licenses/LICENSE) | `6d0d41bfe170ac6c7dc248c9a63e254d0fb45a60d50a8257d0af92c6e249b887` |
| [idna-3.20-LICENSE.txt](idna-3.20-LICENSE.txt) | https://pypi.org/project/idna/3.20/#files (wheel licenses/LICENSE.md) | `1a9a4f0e3d479a27240ddd59a9137a66ab4a0f9dfdc8ca6188cc0bfd85187f04` |
| [libffi-3.4.4-LICENSE.txt](libffi-3.4.4-LICENSE.txt) | https://raw.githubusercontent.com/libffi/libffi/v3.4.4/LICENSE | `2c9c2acb9743e6b007b91350475308aee44691d96aa20eacef8e199988c8c388` |
| [pycryptodome-3.9.4-LICENSE.txt](pycryptodome-3.9.4-LICENSE.txt) | https://github.com/Legrandin/pycryptodome/tree/v3.9.4 (wheel LICENSE.rst) | `d1af3fab2ef8cc53b6c7f48bdeb178ac874b04faf4ba0159a96b6109f1d393e2` |
| [requests-2.32.3-LICENSE.txt](requests-2.32.3-LICENSE.txt) | https://github.com/psf/requests/tree/v2.32.3 (wheel LICENSE) | `09e8a9bcec8067104652c168685ab0931e7868f9c8284b66f5ae6edae5f1130b` |
| [urllib3-2.8.0-LICENSE.txt](urllib3-2.8.0-LICENSE.txt) | https://pypi.org/project/urllib3/2.8.0/#files (wheel licenses/LICENSE.txt) | `130e3a64d5fdd5d096a752694634a7d9df284469de86e5732100268041e3d686` |
| [Chaquopy-pyelftools-0.26-LICENSE.txt](Chaquopy-pyelftools-0.26-LICENSE.txt) | https://raw.githubusercontent.com/chaquo/chaquopy/15.0.1/product/runtime/src/main/python/java/_vendor/pyelftools-0.26.dist-info/LICENSE.txt | `ae18bf4cb82f92af7547259177bc28bc48e4fc732518bcedfe690226288d3445` |
| [Chaquopy-construct-2.06-LICENSE.txt](Chaquopy-construct-2.06-LICENSE.txt) | https://raw.githubusercontent.com/eliben/pyelftools/v0.26/elftools/construct/LICENSE | `f8d0c347a0dcc6ebe1671640dfae8d2411b6ded892e06a6764f8208b218b2af4` |

## 固定源码与重构建入口

- [Chaquopy 15.0.1 完整源码](https://github.com/chaquo/chaquopy/tree/826262dee50f7abfd27edc9072996ddfe2ffbab2)，包括运行时、JNI、Android target 补丁及 Python wheels 的配方。[target 构建版本](https://github.com/chaquo/chaquopy/blob/826262dee50f7abfd27edc9072996ddfe2ffbab2/target/build-all.sh)
- [CPython 3.11.6 官方源码](https://www.python.org/ftp/python/3.11.6/Python-3.11.6.tgz)，完整历史许可及标准库所含第三方说明分别保留在 CPython LICENSE 与 stdlib NOTICES 中。
- [PyCryptodome 3.9.4 源码](https://github.com/Legrandin/pycryptodome/tree/v3.9.4)，Android wheel 的固定配方位于 [Chaquopy 15.0.1 pycryptodome recipe](https://github.com/chaquo/chaquopy/tree/826262dee50f7abfd27edc9072996ddfe2ffbab2/server/pypi/packages/pycryptodome)。其许可证原文含 public-domain、BSD 与所含算法代码的通知。
- [requests 2.32.3](https://github.com/psf/requests/tree/v2.32.3)、[idna 3.20](https://pypi.org/project/idna/3.20/#files)、[urllib3 2.8.0](https://pypi.org/project/urllib3/2.8.0/#files)、[charset-normalizer 3.5.2](https://pypi.org/project/charset-normalizer/3.5.2/#files) 的官方发布页提供对应源码。
- certifi 2026.10.23 保留 MPL-2.0。其 Python 包及 Mozilla CA 证书集合的对应源码可从 [官方同版源码发布](https://pypi.org/project/certifi/2026.10.23/#files) 与 [certifi 官方源码](https://github.com/certifi/python-certifi) 获取。原始 certifi 通知与 MPL-2.0 全文同时随包提供，未修改 certifi 覆盖的文件。
- [OpenSSL 3.0.5](https://github.com/openssl/openssl/tree/openssl-3.0.5)、[SQLite 3.39.2](https://github.com/sqlite/sqlite/tree/version-3.39.2)、[libffi 3.4.4](https://github.com/libffi/libffi/tree/v3.4.4)、[bzip2 1.0.8](https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz)、[xz 5.4.5](https://github.com/tukaani-project/xz/tree/v5.4.5) 保留各自文件许可。target 的 liblzma 部分按 xz COPYING 中对应库声明适用；另附的 GPL/LGPL 文本保留上游完整材料中的引用关系。

用户另行配置的影视 Python 爬虫按设备配置取得，版权与许可属于各自作者。本通知未复制或包含任何用户提供的私有影视脚本。

Chaquopy bootstrap 另包含固定 vendored pyelftools 0.26 及其 Construct 代码，分别保留同版 SDK 的 public-domain 原文与 pyelftools v0.26 所含 Construct 2.06 的 MIT 原文。对应源码位于上述 Chaquopy 固定提交的 `product/runtime/src/main/python/java/_vendor`。
