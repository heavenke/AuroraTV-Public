"""Package newly built dual-ARM native libraries with the unchanged eap29 Java API."""

import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path


ABIS = {"arm64-v8a": (2, 183), "armeabi-v7a": (1, 40)}
LIBRARIES = ("libvlc.so", "libvlcjni.so", "libc++_shared.so")
SOURCE_REFS = {
    "libvlcjni": "a8d53a9151d7e4a9a5dfd0a5eb1cd92669afdc21",
    "vlc": "c84ef1eda4f14f8b57a5b266b51c843cf51ed28b",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def native_entry(path, abi):
    data = path.read_bytes()
    elf_class, machine = ABIS[abi]
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != elf_class or data[5] != 1:
        raise ValueError(f"Invalid ELF class/encoding for {abi}/{path.name}")
    if struct.unpack_from("<H", data, 18)[0] != machine:
        raise ValueError(f"ELF machine does not match {abi}/{path.name}")
    if elf_class == 2:
        offset = struct.unpack_from("<Q", data, 40)[0]
        size, count = struct.unpack_from("<HH", data, 58)
    else:
        offset = struct.unpack_from("<I", data, 32)[0]
        size, count = struct.unpack_from("<HH", data, 46)
    if offset > len(data) or offset + size * count > len(data):
        raise ValueError(f"Truncated ELF section table for {abi}/{path.name}")
    return data


def package(original, native_root, output, retained_assets):
    if original.resolve() == output.resolve():
        raise ValueError("The derived AAR must not overwrite the original Maven archive")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".building")
    manifest = {
        "source_refs": SOURCE_REFS,
        "license_profile": "l (LGPLv3 + ad-clauses, GPL contrib disabled)",
        "android_api": 21,
        "original_aar_sha256": digest(original.read_bytes()),
        "native_libraries": [],
        "assets_removed": [],
        "assets_retained": [],
        "validation": {"native_architecture": True, "java_classes_preserved": False,
                       "source_module_license_audit": "separate_report_required",
                       "device_playback": "not_performed_by_sdk_builder"},
    }
    try:
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as target:
            original_classes = source.read("classes.jar")
            manifest["classes_jar_sha256"] = digest(original_classes)
            for retained in retained_assets:
                if not retained.startswith("assets/") or retained.endswith("/") or retained not in source.namelist():
                    raise ValueError(f"Invalid explicitly retained asset {retained}")
            for entry in source.infolist():
                if entry.filename.startswith("jni/"):
                    continue
                data = source.read(entry)
                if entry.filename.startswith("assets/") and entry.filename not in retained_assets:
                    if not entry.is_dir():
                        manifest["assets_removed"].append({"path": entry.filename, "sha256": digest(data), "size": len(data)})
                    continue
                if entry.filename.startswith("assets/") and not entry.is_dir():
                    manifest["assets_retained"].append({"path": entry.filename, "sha256": digest(data), "size": len(data)})
                target.writestr(entry, data)
            for abi in ABIS:
                for name in LIBRARIES:
                    path = native_root / abi / name
                    data = native_entry(path, abi)
                    entry = zipfile.ZipInfo(f"jni/{abi}/{name}", (2026, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    entry.external_attr = 0o644 << 16
                    target.writestr(entry, data)
                    manifest["native_libraries"].append({"abi": abi, "name": name, "size": len(data), "sha256": digest(data)})
        with zipfile.ZipFile(temporary) as result:
            if result.read("classes.jar") != original_classes:
                raise ValueError("The original Java classes.jar was changed")
            actual = {name for name in result.namelist() if name.startswith("jni/") and not name.endswith("/")}
            expected = {f"jni/{abi}/{name}" for abi in ABIS for name in LIBRARIES}
            if actual != expected:
                raise ValueError("The derived AAR contains unexpected native entries")
        manifest["validation"]["java_classes_preserved"] = True
        temporary.replace(output)
        manifest["derived_aar_sha256"] = digest(output.read_bytes())
        output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        readme = """# LibVLC eap29 派生 SDK

JNI 与 VLC 精确源码引用记录在相邻 manifest。官方构建选择 license l，Android API 21，双 ARM ABI。
classes.jar、AndroidManifest 与 Android res 保留原 Maven 字节，native 三库来自本次源码构建。
实际编入模块的源码授权核验和设备播放验收须结合独立报告，不能仅凭 profile 名字认定全部授权。

本包默认移除原 assets，其中包含 GPL Lua 封面及网页播放脚本，另有未接入的 3D HRTF 数据。
原包没有 TTF、OTF、TTC 字体资产。本应用先通过 NAS、TVBox JAR 或 WebResolver 准备真实 URL，
没有使用 VLC 自带 Twitch 等网页解析、MIDI 或 3D HRTF 功能。字幕仍由 native libass/freetype/harfbuzz
和设备系统字体支持，常规 SRT、ASS、PGS 效果由设备回归确认。
移除项及原始 SHA-256 在 manifest.assets_removed 中逐项列出。显式白名单保留项另列 assets_retained。

使用本 SDK 需要随发布提供所含开源组件的对应源码、补丁、构建步骤和替换/重新链接说明。
本说明不把宿主构建工具或源码树中未编入的代码当作最终 native 授权结论。
"""
        output.with_suffix(".README.md").write_text(readme, encoding="utf-8")
        return manifest
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-aar", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--keep-asset", action="append", default=[])
    args = parser.parse_args()
    manifest = package(args.original_aar, args.native_root, args.output, set(args.keep_asset))
    print(json.dumps({"output": str(args.output), "sha256": manifest["derived_aar_sha256"],
                      "java_classes_preserved": True, "native_libraries": len(manifest["native_libraries"])}))


if __name__ == "__main__":
    main()
