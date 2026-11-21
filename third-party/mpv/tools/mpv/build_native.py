#!/usr/bin/env python3
"""Reproducible Android libmpv build. Run on Linux with a Linux Android NDK (API 21)."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import time
import urllib.request
import uuid
from hardware_codec_selection import apply_hardware_codec_selection
from dolby_vision_codec import apply_dolby_vision_codec
from codec_result_hooks import apply_codec_result_hooks
from codec_rejection_hooks import apply_codec_rejection_hooks
from codec_stage_hooks import apply_codec_stage_hooks
from native_render_ahead import apply_native_render_ahead
from surface_texture_interop import apply_surface_texture_interop
from dolby_vision_mapping import apply_dolby_vision_mapping
from hdr_metadata import apply_hdr_metadata
from hevc_invalid_atc import apply_hevc_invalid_atc

ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads((Path(__file__).with_name('sources.lock.json')).read_text(encoding='utf-8'))
LICENSES = {'mpv': 'LGPL-2.1-or-later', 'ffmpeg': 'LGPL-3.0-or-later', 'mbedtls': 'Apache-2.0',
    'freetype': 'FTL', 'fribidi': 'LGPL-2.1-or-later', 'harfbuzz': 'MIT', 'unibreak': 'Zlib',
    'libxml2': 'MIT', 'fontconfig': 'MIT', 'libass': 'ISC', 'libplacebo': 'LGPL-2.1-or-later', 'dav1d': 'BSD-2-Clause'}
HEVC_EXTRADATA_GUARD = '''    /* A live TS may announce HEVC before its parameter sets are available. */
    if (!avctx->extradata || avctx->extradata_size <= 0)
        return AVERROR_INVALIDDATA;

'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log, env=None, cwd=None):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('a', encoding='utf-8') as output:
        output.write('\n$ ' + shlex.join([str(x) for x in command]) + '\n'); output.flush()
        result = subprocess.run([str(x) for x in command], cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        tail = log.read_text(encoding='utf-8', errors='replace').splitlines()[-28:]
        raise RuntimeError(str(log) + '\n' + '\n'.join(tail))


def prepare_sources(args):
    source_root = args.cache / 'source'
    source_root.mkdir(parents=True, exist_ok=True)
    for name, item in sorted(LOCK['sources'].items(), key=lambda row: row[1].get('destination', row[0]).count('/')):
        archive = args.downloads / item['archive']
        if not archive.is_file():
            args.downloads.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(item['url'], timeout=120) as response:
                archive.write_bytes(response.read())
        if digest(archive) != item['sha256']:
            raise RuntimeError('Source checksum mismatch: ' + name)
        destination = source_root / item.get('destination', name)
        marker = destination / '.aurora-source-sha256'
        if marker.is_file():
            if marker.read_text().strip() != item['sha256']: raise RuntimeError('Unexpected source directory: ' + name)
            continue
        if destination.exists():
            if any(destination.iterdir()): raise RuntimeError('Unmarked source directory is not empty: ' + str(destination))
            destination.rmdir()
        temporary = source_root / ('.unpack-' + name + '-' + uuid.uuid4().hex)
        temporary.mkdir()
        with tarfile.open(archive) as bundle:
            for entry in bundle.getmembers():
                path = Path(entry.name)
                if path.is_absolute() or '..' in path.parts: raise RuntimeError('Unsafe archive path')
                if entry.issym():
                    link = (temporary / path.parent / entry.linkname).resolve()
                    if temporary.resolve() not in link.parents: raise RuntimeError('Unsafe source symlink')
                if entry.islnk() and (Path(entry.linkname).is_absolute() or '..' in Path(entry.linkname).parts):
                    raise RuntimeError('Unsafe source hardlink')
            bundle.extractall(temporary)
        children = list(temporary.iterdir())
        if len(children) != 1 or not children[0].is_dir(): raise RuntimeError('Expected one source archive root')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(children[0]), str(destination))
        temporary.rmdir()
        marker.write_text(item['sha256'] + '\n')
    # Match Android's non-blocking entropy source; keep the change explicit and distributable.
    config = source_root / 'mbedtls/include/mbedtls/mbedtls_config.h'
    text = config.read_text(encoding='utf-8')
    if '"/dev/urandom"' not in text:
        run(['python3', 'scripts/config.py', 'set', 'MBEDTLS_PLATFORM_DEV_RANDOM', '"/dev/urandom"'],
            args.cache / 'prepare-mbedtls.log', cwd=source_root / 'mbedtls')
    # Keep this build-only generator compatible with Ubuntu 20.04's Python 3.8.
    generator = source_root / 'mpv/TOOLS/matroska.py'
    original = generator.read_text(encoding='utf-8')
    if 'from __future__ import annotations' not in original:
        generator.write_text(original.replace('import sys\n', 'from __future__ import annotations\n\nimport sys\n', 1), encoding='utf-8')
    # FFmpeg's HEVC MediaCodec wrapper otherwise passes null into bytestream2_init(),
    # which asserts. Return a decoder-open error so libmpv can fall back safely.
    decoder = source_root / 'ffmpeg/libavcodec/mediacodecdec.c'
    original = decoder.read_text(encoding='utf-8')
    call = '    ret = ff_hevc_decode_extradata(avctx->extradata, avctx->extradata_size,\n'
    if HEVC_EXTRADATA_GUARD + call not in original:
        if original.count(call) != 1:
            raise RuntimeError('Unexpected FFmpeg MediaCodec HEVC source')
        decoder.write_text(original.replace(call, HEVC_EXTRADATA_GUARD + call), encoding='utf-8')
    # Optional observer of actual MediaCodec-rendered frames. The weak call keeps
    # the FFmpeg archive usable on its own, including the HEVC safety test.
    wrapper = source_root / 'ffmpeg/libavcodec/mediacodec_wrapper.c'
    original = wrapper.read_text(encoding='utf-8')
    marker = '\n/* Aurora optional output observer.'
    if marker in original:
        original = original[:original.index(marker)]
    wrapper.write_text(original.rstrip() + '\n' + Path(__file__).with_name('codec_output_hooks.inc').read_text(encoding='utf-8'), encoding='utf-8')
    common = source_root / 'ffmpeg/libavcodec/mediacodecdec_common.c'
    original = common.read_text(encoding='utf-8')
    declaration = 'extern void aurora_mpv_android_codec_started(void *, void *, int, int, int64_t) __attribute__((weak));\n\n'
    start = 'int ff_mediacodec_dec_init(AVCodecContext *avctx, MediaCodecDecContext *s,'
    if declaration not in original:
        if original.count(start) != 1: raise RuntimeError('Unexpected MediaCodec initialization source')
        original = original.replace(start, declaration + start)
    hook = '''    if (aurora_mpv_android_codec_started && s->surface &&
        ((FFANativeWindow *)s->surface)->surface && avctx->codec_type == AVMEDIA_TYPE_VIDEO)
        aurora_mpv_android_codec_started(s->codec, ((FFANativeWindow *)s->surface)->surface,
                                         avctx->width, avctx->height, s->aurora_epoch);

'''
    start = '    av_log(avctx, AV_LOG_DEBUG, "MediaCodec %p started successfully\\n", s->codec);'
    if hook not in original:
        if original.count(start) != 1: raise RuntimeError('Unexpected MediaCodec start source')
        original = original.replace(start, hook + start)
    common.write_text(original, encoding='utf-8')
    original = common.read_text(encoding='utf-8')
    if '#include "jni.h"' not in original:
        original = original.replace('#include "mediacodec.h"\n', '#include "mediacodec.h"\n#include "jni.h"\n')
    # With a JVM, the enumerator has already excluded software video codecs.
    # Do not let an NDK type-only fallback undo that safety guarantee.
    original = original.replace('        if (!s->use_ndk_codec) {\n            return AVERROR_EXTERNAL;',
        '        if (!s->use_ndk_codec || av_jni_get_java_vm(avctx)) {\n            return AVERROR_EXTERNAL;')
    common.write_text(original, encoding='utf-8')
    # Carry the caller's immutable file generation into codec construction.
    # Reading a mutable "current generation" from a delayed codec-start callback
    # could otherwise admit an old decoder after a rapid channel change.
    header = source_root / 'ffmpeg/libavcodec/mediacodecdec_common.h'
    original = header.read_text(encoding='utf-8')
    if 'int64_t aurora_epoch;' not in original:
        if original.count('    bool use_ndk_codec;') != 1: raise RuntimeError('Unexpected MediaCodec context layout')
        original = original.replace('    bool use_ndk_codec;', '    bool use_ndk_codec;\n    int64_t aurora_epoch;')
    if 'int64_t aurora_client;' not in original:
        original = original.replace('    int64_t aurora_epoch;', '    int64_t aurora_epoch;\n    int64_t aurora_client;')
    header.write_text(original, encoding='utf-8')
    original = decoder.read_text(encoding='utf-8')
    if 'int64_t aurora_epoch;' not in original:
        if original.count('    int operating_rate;') != 1: raise RuntimeError('Unexpected MediaCodec decoder layout')
        original = original.replace('    int operating_rate;', '    int operating_rate;\n    int64_t aurora_epoch;')
    if 's->ctx->aurora_epoch = s->aurora_epoch;' not in original:
        original = original.replace('    s->ctx->use_ndk_codec = s->use_ndk_codec;',
            '    s->ctx->use_ndk_codec = s->use_ndk_codec;\n    s->ctx->aurora_epoch = s->aurora_epoch;')
    if 'int64_t aurora_client;' not in original:
        original = original.replace('    int64_t aurora_epoch;', '    int64_t aurora_epoch;\n    int64_t aurora_client;')
    if 's->ctx->aurora_client = s->aurora_client;' not in original:
        original = original.replace('    s->ctx->aurora_epoch = s->aurora_epoch;',
            '    s->ctx->aurora_epoch = s->aurora_epoch;\n    s->ctx->aurora_client = s->aurora_client;')
    option = '''    { "aurora_epoch", "Caller file generation for optional rendered-frame observation",
            OFFSET(aurora_epoch), AV_OPT_TYPE_INT64, {.i64 = 0}, 0, INT64_MAX, VD },
'''
    if option not in original:
        original = original.replace('static const AVOption ff_mediacodec_vdec_options[] = {\n',
            'static const AVOption ff_mediacodec_vdec_options[] = {\n' + option)
    client_option = '''    { "aurora_client", "Caller session identity for optional hardware-codec result observation",
            OFFSET(aurora_client), AV_OPT_TYPE_INT64, {.i64 = 0}, 0, INT64_MAX, VD },
'''
    if client_option not in original:
        original = original.replace('static const AVOption ff_mediacodec_vdec_options[] = {\n',
            'static const AVOption ff_mediacodec_vdec_options[] = {\n' + client_option)
    decoder.write_text(original, encoding='utf-8')
    original = decoder.read_text(encoding='utf-8')
    timing_log = '''        av_log(avctx, AV_LOG_VERBOSE,
               "HEVC timing VUI=%u/%u poc=%d:%d field=%d VPS=%u/%u\\n",
               sps->vui.vui_time_scale, sps->vui.vui_num_units_in_tick,
               sps->vui.vui_poc_proportional_to_timing_flag,
               sps->vui.vui_num_ticks_poc_diff_one_minus1 + 1, sps->vui.field_seq_flag,
               vps->vps_time_scale, vps->vps_num_units_in_tick);
'''
    if timing_log not in original:
        marker = '        avctx->level   = sps->ptl.general_ptl.level_idc;\n'
        if original.count(marker) != 1: raise RuntimeError('Unexpected HEVC parameter metadata')
        decoder.write_text(original.replace(marker, marker + timing_log), encoding='utf-8')
    # A TextureView consumes a timestamped buffer, independently of the delayed
    # informational OnFrameRendered notification. The application still requires
    # an actual TextureView update matching this exact ticket before showing it.
    public = source_root / 'ffmpeg/libavcodec/mediacodec.c'
    original = public.read_text(encoding='utf-8')
    declaration = '''#include "mediacodec_surface.h"
#include "libavutil/time.h"
extern int64_t aurora_mpv_android_prepare_texture_frame(void *, int64_t, int64_t) __attribute__((weak));
extern void aurora_mpv_android_texture_frame_submitted(void *, int64_t, int64_t, int, int64_t) __attribute__((weak));
'''
    if declaration not in original:
        original = original.replace('#include "mediacodecdec_common.h"\n', '#include "mediacodecdec_common.h"\n' + declaration)
    timed_release = '''        void *surface = ctx->surface ? ((FFANativeWindow *)ctx->surface)->surface : NULL;
        int64_t stamp = render && surface && aurora_mpv_android_prepare_texture_frame &&
            aurora_mpv_android_texture_frame_submitted ?
            aurora_mpv_android_prepare_texture_frame(surface, ctx->aurora_epoch, buffer->pts) : 0;
        if (stamp > 0) {
            int64_t begin = av_gettime_relative();
            int result = ff_AMediaCodec_releaseOutputBufferAtTime(ctx->codec, buffer->index, stamp);
            aurora_mpv_android_texture_frame_submitted(surface, ctx->aurora_epoch, stamp,
                result, (av_gettime_relative() - begin) * 1000);
            return result;
        }
        if (stamp < 0)
            return ff_AMediaCodec_releaseOutputBuffer(ctx->codec, buffer->index, 0);
'''
    marker = '        return ff_AMediaCodec_releaseOutputBuffer(ctx->codec, buffer->index, render);'
    if timed_release not in original:
        if original.count(marker) != 1: raise RuntimeError('Unexpected MediaCodec buffer release source')
        original = original.replace(marker, timed_release + marker)
    public.write_text(original, encoding='utf-8')
    apply_hardware_codec_selection(source_root / 'ffmpeg')
    apply_dolby_vision_codec(source_root / 'ffmpeg')
    apply_codec_rejection_hooks(source_root / 'ffmpeg')
    apply_codec_result_hooks(source_root / 'ffmpeg')
    apply_codec_stage_hooks(source_root / 'ffmpeg')
    apply_native_render_ahead(source_root / 'mpv')
    apply_surface_texture_interop(source_root / 'mpv')
    apply_dolby_vision_mapping(source_root / 'mpv')
    apply_hdr_metadata(source_root / 'mpv')
    apply_hevc_invalid_atc(source_root / 'ffmpeg')
    return source_root


def build_abi(args, sources, abi):
    work = args.cache / 'lgpl3-api21-v1' / abi
    prefix = work / 'prefix'
    prefix.mkdir(parents=True, exist_ok=True)
    pkgdir = prefix / 'lib/pkgconfig'
    pkgdir.mkdir(parents=True, exist_ok=True)
    zlib_header = (args.ndk / 'toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include/zlib.h').read_text()
    zlib_version = re.search(r'#define ZLIB_VERSION "([^"]+)"', zlib_header)[1]
    (pkgdir / 'zlib.pc').write_text('# NDK header version; runtime zlib is supplied by Android.\n'
        'Name: zlib\nDescription: Android system zlib\nVersion: ' + zlib_version + '\nLibs: -lz\n')
    # Android provides these link stubs/headers through the NDK, not pkg-config files.
    for name, version, library in [('egl', '1.5', 'EGL'), ('glesv2', '3.2', 'GLESv2')]:
        (pkgdir / (name + '.pc')).write_text('Name: Android ' + name + '\nDescription: Android NDK system graphics\n'
            'Version: ' + version + '\nLibs: -l' + library + '\n')
    tools = args.ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin'
    target = 'aarch64-linux-android' if abi == 'arm64-v8a' else 'armv7a-linux-androideabi'
    host = 'aarch64-linux-android' if abi == 'arm64-v8a' else 'arm-linux-androideabi'
    cc = tools / (target + '21-clang'); cxx = tools / (target + '21-clang++')
    flags = ['-fPIC', '-O2', '-ffunction-sections', '-fdata-sections', '-fvisibility=hidden']
    env = dict(os.environ, PATH=str(tools) + ':' + str(args.host_tools) + ':/usr/local/bin:/usr/bin:/bin',
        CC=str(cc), CXX=str(cxx), AR=str(tools/'llvm-ar'), RANLIB=str(tools/'llvm-ranlib'),
        STRIP=str(tools/'llvm-strip'), CFLAGS=' '.join(flags), CXXFLAGS=' '.join(flags),
        CPPFLAGS='-I'+str(prefix/'include'), LDFLAGS='-L'+str(prefix/'lib'),
        PKG_CONFIG_LIBDIR=str(prefix/'lib/pkgconfig'), PKG_CONFIG_PATH='', LC_ALL='C.UTF-8')
    meson_env = dict(env)
    for key in ['CC','CXX','AR','RANLIB','STRIP','CFLAGS','CXXFLAGS','CPPFLAGS','LDFLAGS']:
        meson_env.pop(key, None)
    cross = work / 'android-cross.ini'
    cross.write_text("[binaries]\nc = " + repr(str(cc)) + "\ncpp = " + repr(str(cxx)) +
        "\nar = " + repr(str(tools/'llvm-ar')) + "\nstrip = " + repr(str(tools/'llvm-strip')) +
        "\npkg-config = '/usr/bin/pkg-config'\n[host_machine]\nsystem = 'android'\ncpu_family = " +
        repr('aarch64' if abi=='arm64-v8a' else 'arm') + "\ncpu = " + repr('armv8-a' if abi=='arm64-v8a' else 'armv7-a') +
        "\nendian = 'little'\n[properties]\nneeds_exe_wrapper = true\n[built-in options]\nc_args = " + repr(flags) +
        "\ncpp_args = " + repr(flags) + "\ncpp_link_args = ['-static-libstdc++']\n")

    def step(name, commands, working=None, step_env=None, source_stamp=None):
        configuration = hashlib.sha256(json.dumps(commands, default=str, sort_keys=True).encode()).hexdigest()
        stamp = work / (name + '.done.json')
        expected = {'configuration': configuration, 'sourceStamp': source_stamp}
        cached = json.loads(stamp.read_text()) if stamp.is_file() else {}
        if all(cached.get(key) == value for key, value in expected.items()):
            print(abi, name, 'cached', flush=True); return
        print(abi, name, 'building', flush=True)
        started = time.monotonic()
        for command in commands: run(command, work/'logs'/(name+'.log'), env=step_env or env, cwd=working)
        stamp.write_text(json.dumps({**expected, 'seconds': round(time.monotonic()-started,2)}))
        print(abi, name, 'complete', flush=True)

    def cmake(name, options):
        build = work / ('build-' + name)
        configure = [str(args.host_tools/'cmake'), '-S', str(sources/name), '-B', str(build), '-G','Ninja',
            '-DCMAKE_TOOLCHAIN_FILE='+str(args.ndk/'build/cmake/android.toolchain.cmake'),
            '-DANDROID_ABI='+abi,'-DANDROID_PLATFORM=android-21','-DANDROID_STL=c++_static',
            '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_INSTALL_PREFIX='+str(prefix),'-DCMAKE_INSTALL_LIBDIR=lib',
            '-DCMAKE_POSITION_INDEPENDENT_CODE=ON','-DBUILD_SHARED_LIBS=OFF',
            '-DCMAKE_C_FLAGS='+' '.join(flags),'-DCMAKE_CXX_FLAGS='+' '.join(flags), *options]
        step(name,[configure,[str(args.host_tools/'cmake'),'--build',str(build),'-j',str(args.jobs)],
            [str(args.host_tools/'cmake'),'--install',str(build)]],step_env=meson_env)

    def meson(name, options):
        build = work / ('build-' + name)
        configure = [str(args.meson),'setup',str(build),str(sources/name),'--cross-file',str(cross),
            '--prefix',str(prefix),'--libdir','lib','--buildtype','release','--default-library','static',
            '--auto-features','disabled','--wrap-mode','nodownload','-Db_staticpic=true',*options]
        if (build/'build.ninja').is_file(): configure.insert(2,'--reconfigure')
        step(name,[configure,['ninja','-C',str(build),'-j',str(args.jobs)],['ninja','-C',str(build),'install']],step_env=meson_env)

    if args.stage not in ('link', 'core'):
        cmake('mbedtls',['-DENABLE_PROGRAMS=OFF','-DENABLE_TESTING=OFF','-DUSE_SHARED_MBEDTLS_LIBRARY=OFF',
            '-DUSE_STATIC_MBEDTLS_LIBRARY=ON','-DMBEDTLS_FATAL_WARNINGS=OFF'])
        cmake('freetype',['-DFT_DISABLE_ZLIB=OFF','-DFT_DISABLE_BZIP2=ON','-DFT_DISABLE_PNG=ON',
            '-DFT_DISABLE_HARFBUZZ=ON','-DFT_DISABLE_BROTLI=ON'])
        meson('fribidi',['-Ddocs=false','-Dbin=false','-Dtests=false'])
        meson('harfbuzz',['-Dtests=disabled','-Ddocs=disabled','-Dutilities=disabled','-Dfreetype=enabled',
            '-Draster=disabled','-Dvector=disabled','-Dgpu=disabled','-Dsubset=disabled'])
        build = work/'build-unibreak';build.mkdir(exist_ok=True)
        step('unibreak',[[str(sources/'unibreak/configure'),'--prefix='+str(prefix),'--host='+host,
            '--enable-static','--disable-shared','--with-pic'],['make','-j'+str(args.jobs)],['make','install']],working=build)
        cmake('libxml2',['-DLIBXML2_WITH_PYTHON=OFF','-DLIBXML2_WITH_PROGRAMS=OFF','-DLIBXML2_WITH_TESTS=OFF',
            '-DLIBXML2_WITH_ICONV=OFF','-DLIBXML2_WITH_ICU=OFF','-DLIBXML2_WITH_LZMA=OFF'])
        meson('fontconfig',['-Dtests=disabled','-Ddoc=disabled','-Dtools=disabled','-Dnls=disabled',
            '-Dcache-build=disabled','-Dxml-backend=libxml2','-Ddefault-fonts-dirs=/system/fonts',
            '-Dadditional-fonts-dirs=[]'])
        meson('libass',['-Dfontconfig=enabled','-Dlibunibreak=enabled'])
        meson('dav1d',['-Denable_tools=false','-Denable_tests=false'])
        build = work/'build-ffmpeg';build.mkdir(exist_ok=True)
        ffargs = [str(sources/'ffmpeg/configure'),'--prefix='+str(prefix),'--target-os=android','--enable-cross-compile',
            '--arch='+('aarch64' if abi=='arm64-v8a' else 'arm'),'--cpu='+('armv8-a' if abi=='arm64-v8a' else 'armv7-a'),
            '--cc='+str(cc),'--cxx='+str(cxx),'--ar='+str(tools/'llvm-ar'),'--ranlib='+str(tools/'llvm-ranlib'),
            '--nm='+str(tools/'llvm-nm'),'--strip='+str(tools/'llvm-strip'),'--pkg-config=/usr/bin/pkg-config',
            '--pkg-config-flags=--static','--extra-cflags='+' '.join(flags)+' -I'+str(prefix/'include'),
            '--extra-ldflags=-L'+str(prefix/'lib'),'--disable-shared','--enable-static','--enable-pic',
            '--disable-gpl','--disable-nonfree','--enable-version3','--enable-jni','--enable-mediacodec',
            '--enable-bsf=hevc_metadata',
            '--enable-mbedtls','--enable-libxml2','--enable-libdav1d','--disable-vulkan','--disable-programs',
            '--disable-doc','--disable-devices','--disable-muxers','--disable-encoders','--disable-avdevice']
        step('ffmpeg',[ffargs,['make','-j'+str(args.jobs)],['make','install']],working=build)
        configuration=(build/'config.h').read_text()
        for macro,value in [('CONFIG_GPL',0),('CONFIG_NONFREE',0),('CONFIG_VERSION3',1)]:
            if '#define '+macro+' '+str(value) not in configuration:raise RuntimeError('Unexpected FFmpeg license: '+macro)
        meson('libplacebo',['-Ddovi=enabled','-Dlibdovi=disabled','-Dvulkan=disabled','-Dopengl=enabled','-Dgl-proc-addr=enabled','-Dd3d11=disabled',
            '-Dglslang=disabled','-Dshaderc=disabled','-Ddemos=false','-Dtests=false','-Dbench=false'])
        meson('mpv',['-Dgpl=false','-Dlibmpv=true','-Dcplayer=false','-Dbuild-date=false','-Dmanpage-build=disabled',
            '-Dlua=disabled','-Djavascript=disabled','-Dlibcurl=disabled','-Dlibavdevice=disabled',
            '-Dgl=enabled','-Dplain-gl=enabled','-Degl=enabled','-Degl-android=enabled','-Dandroid-media-ndk=enabled',
            '-Daudiotrack=enabled','-Dopensles=enabled','-Dzlib=enabled','-Dvector=enabled'])
        options=json.loads((work/'build-mpv/meson-info/intro-buildoptions.json').read_text())
        if next(row['value'] for row in options if row['name']=='gpl') is not False:raise RuntimeError('GPL mpv build rejected')

    # A link/core build may reuse an older prefix with auto-features=disabled.
    # Enable the internal LGPL reshaper explicitly; libdovi/Rust is not needed.
    if args.stage in ('link', 'core'):
        meson('libplacebo',['-Ddovi=enabled','-Dlibdovi=disabled','-Dvulkan=disabled','-Dopengl=enabled','-Dgl-proc-addr=enabled','-Dd3d11=disabled',
            '-Dglslang=disabled','-Dshaderc=disabled','-Ddemos=false','-Dtests=false','-Dbench=false'])
    placebo_config = (prefix/'include/libplacebo/config.h').read_text()
    if '#define PL_HAVE_DOVI 1' not in placebo_config:
        raise RuntimeError('Dolby Vision reshaping was not enabled in libplacebo')

    # Refresh the patched archive even when the configure/build was cached.
    ffmpeg_root = sources / 'ffmpeg'
    ffmpeg_inputs = [ffmpeg_root / name for name in (
        'configure', 'libavcodec/mediacodec.c', 'libavcodec/mediacodecdec.c',
        'libavcodec/mediacodecdec_common.c', 'libavcodec/mediacodecdec_common.h',
        'libavcodec/mediacodec_wrapper.c', 'libavcodec/mediacodec_wrapper.h', 'libavcodec/bsf/h265_metadata.c',
        'libavcodec/bsf/aurora_hevc_invalid_atc.inc', 'libavcodec/bsf/aurora_hevc_invalid_atc_filter.inc',
        'libavcodec/bsf/aurora_hevc_hlg_atc.inc')]
    ffmpeg_inputs += sorted(path for path in (ffmpeg_root / 'libavcodec').glob('cbs*')
                            if path.suffix in ('.c', '.h'))
    ffmpeg_source_stamp = hashlib.sha256(''.join(digest(path) for path in ffmpeg_inputs).encode()).hexdigest()
    ffmpeg_build = work/'build-ffmpeg'
    step('ffmpeg-hevc-guard', [['make', '-j'+str(args.jobs)], ['make', 'install']],
         working=ffmpeg_build, source_stamp=ffmpeg_source_stamp)

    # The link-only path must also refresh a locally patched native VO.
    mpv_source_stamp = digest(sources / 'mpv/video/out/vo_mediacodec_embed.c')
    texture_inputs = [sources / 'mpv' / name for name in (
        'video/out/hwdec/hwdec_surfacetexture.c', 'video/out/gpu/hwdec.c',
        'video/out/gpu/hwdec.h', 'video/out/gpu/video.c', 'video/hwdec.c',
        'video/hwdec.h', 'video/decode/vd_lavc.c', 'video/mp_image.c',
        'video/mp_image.h', 'meson.build', 'video/out/gpu/shader_cache.c',
        'video/out/gpu/shader_cache.h', 'video/out/gpu/aurora_dolby_vision_mapping.inc',
        'video/out/opengl/common.c', 'player/command.c')]
    texture_source_stamp = hashlib.sha256(''.join(digest(path) for path in texture_inputs).encode()).hexdigest()
    step('mpv-native-output', [['ninja', '-C', str(work/'build-mpv'), '-j', str(args.jobs)],
         ['ninja', '-C', str(work/'build-mpv'), 'install']], step_env=meson_env,
         source_stamp=mpv_source_stamp + ':' + texture_source_stamp)

    if args.stage != 'dependencies':
        bridge=ROOT/'app/src/main/cpp/mpv_jni.c'
        if args.stage != 'core' and not bridge.is_file():raise RuntimeError('The JNI bridge source is missing')
        output=args.output/abi;output.mkdir(parents=True,exist_ok=True)
        obj=output/'mpv_jni.o'
        exports=Path(__file__).with_name('exports.map')
        log=work/'logs/jni.log'
        core_obj=output/'android_env.o'
        run([cc,*flags,'-std=c11','-I'+str(prefix/'include'),'-c',Path(__file__).with_name('android_env.c'),'-o',core_obj],log,env=env)
        libs=subprocess.check_output(['/usr/bin/pkg-config','--static','--libs','mpv'],env=env,text=True).strip()
        linklibs=[x for x in shlex.split(libs) if x not in ('-lstdc++','-lc++')]
        run([cxx,'-shared','-static-libstdc++','-Wl,--no-undefined','-Wl,--gc-sections','-Wl,-Bsymbolic',
            '-Wl,-soname,libaurora_mpv_core.so','-Wl,-z,max-page-size=16384',
            '-Wl,--version-script='+str(Path(__file__).with_name('core_exports.map')),
            core_obj,'-Wl,--whole-archive',prefix/'lib/libmpv.a','-Wl,--no-whole-archive',
            '-Wl,--start-group',*linklibs,'-Wl,--end-group','-lEGL','-lGLESv2','-landroid','-llog','-lz','-latomic',
            '-o',output/'libaurora_mpv_core.so'],log,env=env)
        if args.stage != 'core':
            run([cc,*flags,'-std=c11','-D_GNU_SOURCE','-I'+str(prefix/'include'),'-c',bridge,'-o',obj],log,env=env)
            run([cc,'-shared','-Wl,--no-undefined','-Wl,--gc-sections','-Wl,-Bsymbolic','-Wl,-soname,libaurora_mpv.so',
                '-Wl,-z,max-page-size=16384','-Wl,--version-script='+str(exports),obj,'-L'+str(output),'-laurora_mpv_core',
                '-lEGL','-lGLESv2','-landroid','-llog','-lm',
                '-o',output/'libaurora_mpv.so'],log,env=env)
        run([tools/'llvm-strip','--strip-unneeded',output/'libaurora_mpv_core.so'],log,env=env)
        if args.stage != 'core':run([tools/'llvm-strip','--strip-unneeded',output/'libaurora_mpv.so'],log,env=env)
        dynamic=subprocess.check_output([str(tools/'llvm-readelf'),'-d',str(output/'libaurora_mpv_core.so')],text=True)
        if 'libc++_shared' in dynamic or 'libavcodec.so' in dynamic:raise RuntimeError('Unexpected shared SDK dependency')
        (output/'build-manifest.json').write_text(json.dumps({'abi':abi,'androidApi':21,'mpv':'0.42.0',
            'license':'LGPL-3.0-or-later combined native component','gpl':False,'nonfree':False,
            **({'sha256':digest(output/'libaurora_mpv.so'),'bytes':(output/'libaurora_mpv.so').stat().st_size,
                'bridgeObjectSha256':digest(obj)} if args.stage != 'core' else {}),
            'coreSha256':digest(output/'libaurora_mpv_core.so'),'coreBytes':(output/'libaurora_mpv_core.so').stat().st_size,
            'ffmpegMediaCodecSourceSha256':ffmpeg_source_stamp,
            'dolbyVisionCodecPatchSha256':hashlib.sha256(''.join(digest(Path(__file__).with_name(name)) for name in
                ('dolby_vision_codec.py', 'dolby_vision_codec.inc')).encode()).hexdigest(),
            'mpvNativeOutputSourceSha256':mpv_source_stamp,
            'mpvTextureInteropSourceSha256':texture_source_stamp,
            'mpvHdrMetadataSourceSha256':digest(sources/'mpv/player/command.c'),
            'androidEnvironmentSourceSha256':digest(Path(__file__).with_name('android_env.c')),
            'sourcesLockSha256':digest(Path(__file__).with_name('sources.lock.json')),
            'dependencies':LICENSES},indent=2)+'\n')
    return {'abi':abi,'prefix':str(prefix),'complete':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndk',type=Path,required=True)
    parser.add_argument('--cache',type=Path,default=Path.home()/'.cache/aurora-mpv')
    parser.add_argument('--downloads',type=Path,required=True)
    parser.add_argument('--host-tools',type=Path,default=Path('/root/.cache/aurora-vlc-lgpl/source/vlc/extras/tools/build/bin'))
    parser.add_argument('--meson',type=Path,default=Path('/root/.cache/aurora-mpv/build-tools/python/bin/meson'))
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/mpv-native-build')
    parser.add_argument('--abi',choices=['arm64-v8a','armeabi-v7a','all'],default='all')
    parser.add_argument('--jobs',type=int,default=6)
    parser.add_argument('--stage',choices=['all','dependencies','link','core'],default='all')
    args=parser.parse_args()
    if os.name!='posix':raise SystemExit('Use a Linux host and Linux NDK')
    args.cache=args.cache.resolve();args.cache.mkdir(parents=True,exist_ok=True)
    sources=prepare_sources(args)
    abis=['arm64-v8a','armeabi-v7a'] if args.abi=='all' else [args.abi]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(abis)) as pool:
        for result in pool.map(lambda abi:build_abi(args,sources,abi),abis):print(json.dumps(result),flush=True)


if __name__=='__main__':main()
