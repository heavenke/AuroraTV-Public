# 许可证原文来源

下列文件以原始字节保存自相应官方项目。SHA-256可用于核对本仓库保存的文本。组件的实际版本与使用方式见根目录THIRD_PARTY_NOTICES.md。

LGPL 3.0 原文引用 GPL 3.0 的基础条款，两份原文一起提供。各组件具体适用的版本与附加条款，以该组件及其文件声明为准。

| 文件 | 官方来源 | SHA-256 |
| --- | --- | --- |
| [Apache-2.0.txt](Apache-2.0.txt) | [官方原文](https://www.apache.org/licenses/LICENSE-2.0.txt) | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| [LGPL-2.1.txt](LGPL-2.1.txt) | [官方原文](https://raw.githubusercontent.com/bilibili/ijkplayer/master/COPYING.LGPLv2.1) | `b634ab5640e258563c536e658cad87080553df6f34f62269a21d554844e58bfe` |
| [CC0-1.0.txt](CC0-1.0.txt) | [官方原文](https://raw.githubusercontent.com/str4d/ed25519-java/master/LICENSE.txt) | `259d4aabe1101af0861bf563a0f07f6866a9049532450a5f7175b3bc7b9fedf0` |
| [OpenSSL-1.1.1w-LICENSE.txt](OpenSSL-1.1.1w-LICENSE.txt) | [官方原文](https://raw.githubusercontent.com/openssl/openssl/OpenSSL_1_1_1w/LICENSE) | `c32913b33252e71190af2066f08115c69bc9fddadf3bf29296e20c835389841c` |
| [OpenSSL-1.0.2q-LICENSE.txt](OpenSSL-1.0.2q-LICENSE.txt) | [官方原文](https://raw.githubusercontent.com/openssl/openssl/OpenSSL_1_0_2q/LICENSE) | `c8f60f4842bbad0353f5d81620e72b168b5638ca3a0a999f5da113b22491612e` |
| [LLVM-libcxx-LICENSE.txt](LLVM-libcxx-LICENSE.txt) | [NDK r28c 对应原文](https://android.googlesource.com/toolchain/llvm-project/+/97a699bf4812a18fb657c2779f5296a4ab2694d2/libcxx/LICENSE.TXT) | `539dd7aed86e8a4f12cbdd0e6c50c189c7d74847e4fecc64ce2c6ee3a01da38b` |
| [ZXing-NOTICE.txt](ZXing-NOTICE.txt) | [官方原文](https://raw.githubusercontent.com/zxing/zxing/zxing-3.5.3/NOTICE) | `4db4b60aace29ec6c5c4f13ca9cac1930d3c0c54bcc67dceead0c10771120e66` |
| [dexlib2-NOTICE.txt](dexlib2-NOTICE.txt) | [smali v2.5.2 官方原文](https://raw.githubusercontent.com/JesusFreke/smali/v2.5.2/NOTICE) | `e247d92c57251fc3e674b5366bafd40ed644bfc7c4a55172e464685a25622945` |
| [LGPL-3.0.txt](LGPL-3.0.txt) | [GNU官方说明](https://www.gnu.org/licenses/lgpl-3.0.txt) / [保存文本来源](https://www.gnu.org/licenses/lgpl-3.0.txt) | `e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118` |
| [GPL-3.0.txt](GPL-3.0.txt) | [GNU官方说明](https://www.gnu.org/licenses/gpl-3.0.txt) / [保存文本来源](https://www.gnu.org/licenses/gpl-3.0.txt) | `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986` |
| [LLVM-libcxxabi-LICENSE.txt](LLVM-libcxxabi-LICENSE.txt) | [NDK r28c 对应原文](https://android.googlesource.com/toolchain/llvm-project/+/97a699bf4812a18fb657c2779f5296a4ab2694d2/libcxxabi/LICENSE.TXT) | `e2b35be49f7284a45b7baca8fc7b3ab7440e7902392b2528a457816b5bb2a15c` |
| [LLVM-libunwind-LICENSE.txt](LLVM-libunwind-LICENSE.txt) | [NDK r28c 对应原文](https://android.googlesource.com/toolchain/llvm-project/+/97a699bf4812a18fb657c2779f5296a4ab2694d2/libunwind/LICENSE.TXT) | `b5efebcaca80879234098e52d1725e6d9eb8fb96a19fce625d39184b705f7b6d` |
| [VLC-contrib-NOTICES.txt](VLC-contrib-NOTICES.txt) | 同版本源码附件中 rebuilt-libvlc/contrib-notices 的 222 份原文，分节保存来源归档、路径及原文 SHA-256 | `245d26fb744eb022eb0a1d068916f3fef083f3b895b5f10e45bad40dce4af9a6` |

## 对应源码与构建资料

公众版仓库提供第三方源码与构建资料，其中的清单记录版本、固定上游提交、补丁、构建配置、来源及校验值。按对应清单查阅每个组成部分的版权与许可。[第三方材料](https://github.com/heavenke/AuroraTV-Public/tree/main/third-party)

共享库替换、重新链接、APK 自签及更新流程见专门说明。[第三方共享库替换与重新打包](../Library-replacement.md)

DEX 适配依赖固定为 dexlib2 2.5.2 与 Guava 33.3.1-android。对应源码分别来自 [dexlib2 2.5.2 源码制品](https://repo.maven.apache.org/maven2/org/smali/dexlib2/2.5.2/dexlib2-2.5.2-sources.jar)、[smali v2.5.2](https://github.com/JesusFreke/smali/tree/v2.5.2/dexlib2) 与 [Guava 33.3.1-android 源码制品](https://repo.maven.apache.org/maven2/com/google/guava/guava/33.3.1-android/guava-33.3.1-android-sources.jar)。JSR-305 3.0.2 注解的 [固定源码制品](https://repo.maven.apache.org/maven2/com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2-sources.jar) 沿用其 Apache-2.0 声明。

## 配置页面兼容代码

- core-js 3.51.0 的 LICENSE 原文来自锁定 npm 包，项目来源 https://github.com/zloirock/core-js，原文 SHA-256 为 `b87653fff2d44426ab5cd4723cee3b1364dc8d35a0acdf098c54689543123bf8`。
- Babel runtime helpers 7.29.14 的 LICENSE 原文来自锁定 npm 包，项目来源 https://github.com/babel/babel，原文 SHA-256 为 `4be9d87b56a306293223b490c0d0b245e9e94f39884147bf051a6c7b825aeb30`。

合集文件 `Config-web-runtime-LICENSE.txt` 的 SHA-256 为 `592cfcdf3c3fe98e9ed6b86177313ad5de826bab47edf83842f0776df8570f5c`。构建依赖锁定在 `tools/config-web/package-lock.json`，对应离线页面随 APK 提供。
