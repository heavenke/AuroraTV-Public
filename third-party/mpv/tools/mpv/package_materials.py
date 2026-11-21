#!/usr/bin/env python3
"""Collect verified corresponding sources, build recipe, manifests and in-APK notices."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads', type=Path, required=True)
    parser.add_argument('--native', type=Path, default=ROOT/'artifacts/mpv-native-build')
    parser.add_argument('--ndk', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'out/third-party/mpv-0.42.0-corresponding-source.zip')
    args = parser.parse_args()
    recipe = Path(__file__).parent
    lock = json.loads((recipe/'sources.lock.json').read_text(encoding='utf-8'))
    notices = ROOT/'app/src/main/assets/third_party/MPV'
    notices.mkdir(parents=True, exist_ok=True)
    materials = {}
    for name, source in lock['sources'].items():
        archive = args.downloads/source['archive']
        if digest(archive) != source['sha256']:
            raise RuntimeError('Source digest mismatch: ' + name)
        materials['downloads/'+archive.name] = archive
        with tarfile.open(archive) as bundle:
            for member in bundle.getmembers():
                if not member.isfile() or '/' not in member.name:
                    continue
                relative = member.name.split('/', 1)[1]
                top_license = '/' not in relative and any(word in relative.lower() for word in ('licen', 'copy', 'notice'))
                freetype_license = name == 'freetype' and relative in ('docs/FTL.TXT', 'docs/GPLv2.TXT')
                if top_license or freetype_license:
                    target = notices/name/relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(bundle.extractfile(member).read())
    # libc++/libc++abi and compiler support are linked privately, preserving other SDK runtimes.
    for name in ('NOTICE', 'NOTICE.toolchain'):
        text = args.ndk/name
        if not text.is_file(): raise RuntimeError('Missing NDK notice: '+name)
        (notices/('NDK-'+name)).write_bytes(text.read_bytes())
    for name in ('build_native.py', 'sources.lock.json', 'android_env.c', 'codec_output_hooks.inc', 'codec_result_hooks.py', 'codec_result_hooks.inc', 'codec_rejection_hooks.py', 'codec_rejection_hooks.inc', 'codec_stage_hooks.py', 'codec_stage_hooks.inc', 'hardware_codec_selection.py', 'hardware_codec_selection.inc', 'hevc_invalid_atc.py', 'hevc_invalid_atc.inc', 'hevc_invalid_atc_filter.inc', 'hevc_hlg_atc.inc', 'native_render_ahead.py', 'core_exports.map', 'exports.map', 'README.md', 'package_materials.py'):
        materials['tools/mpv/'+name] = recipe/name
    for pattern in ('*.c', '*.py'):
        for test in (recipe/'tests').glob(pattern):
            materials['tools/mpv/tests/'+test.name] = test
    for name in ('surface_texture_interop.py', 'surface_texture_interop.c', 'dolby_vision_codec.py', 'dolby_vision_codec.inc',
                 'dolby_vision_mapping.py', 'dolby_vision_mapping.inc', 'hdr_metadata.py'):
        materials['tools/mpv/'+name] = recipe/name
    bridge_source = ROOT/'app/src/main/cpp/mpv_jni.c'
    # The replaceable LGPL core is public; the application's thin JNI remains
    # proprietary. Validate it when packaging from the app tree, never publish it.
    for abi in ('arm64-v8a', 'armeabi-v7a'):
        manifest_path = args.native/abi/'build-manifest.json'
        manifest = json.loads(manifest_path.read_text())
        if manifest['coreSha256'] != digest(args.native/abi/'libaurora_mpv_core.so'):
            raise RuntimeError('Native digest mismatch: '+abi)
        if bridge_source.is_file() and manifest.get('bridgeSourceSha256') and manifest['bridgeSourceSha256'] != digest(bridge_source):
            raise RuntimeError('JNI bridge source digest mismatch: '+abi)
        materials['manifests/'+abi+'.json'] = manifest_path
    for notice in notices.rglob('*'):
        if notice.is_file(): materials['licenses/'+notice.relative_to(notices).as_posix()] = notice
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in sorted(materials.items()): archive.write(path, name)
        archive.writestr('SHA256SUMS', ''.join(digest(path)+'  '+name+'\n' for name, path in sorted(materials.items())))
    args.output.with_suffix('.zip.sha256').write_text(digest(args.output)+'  '+args.output.name+'\n', encoding='utf-8')
    print(args.output.name, args.output.stat().st_size, digest(args.output))


if __name__ == '__main__':
    main()
