"""Opt-in Dolby Vision MIME/profile selection for the pinned FFmpeg source.

Requires the existing hardware codec selector. No renderer, software fallback,
device model exception, network probe or ordinary HEVC policy is changed.
All four target files are validated before any write.
"""
from pathlib import Path

RECIPE = Path(__file__).resolve().parent


def _replace(source, before, after, label):
    if after in source:
        if source.count(after) != 1:
            raise RuntimeError('Duplicate Dolby patch: ' + label)
        return source
    if source.count(before) != 1:
        raise RuntimeError('Unexpected Dolby patch anchor: ' + label)
    return source.replace(before, after, 1)


def apply_dolby_vision_codec(ffmpeg_source: Path) -> bool:
    root = Path(ffmpeg_source) / 'libavcodec'
    files = {name: (root / name).read_text(encoding='utf-8') for name in
             ('mediacodecdec.c', 'mediacodecdec_common.c', 'mediacodec_wrapper.c', 'mediacodec_wrapper.h')}
    patched = dict(files)
    decoder = patched['mediacodecdec.c']
    decoder = _replace(decoder, '#include "libavutil/common.h"\n',
                       '#include "libavutil/common.h"\n#include "libavutil/dovi_meta.h"\n', 'metadata header')
    decoder = _replace(decoder, '    int operating_rate;\n',
                       '    int operating_rate;\n    int aurora_dovi;\n    int aurora_dovi_profile;\n', 'options state')
    anchor = 'static av_cold int mediacodec_decode_init(AVCodecContext *avctx)\n'
    helper = (RECIPE / 'dolby_vision_codec.inc').read_text(encoding='utf-8')
    if '/* Aurora opt-in Dolby Vision MediaCodec' in decoder and helper not in decoder:
        raise RuntimeError('Changed Dolby helper in an already patched source')
    decoder = _replace(decoder, anchor,
                       helper + '\n' + anchor,
                       'format helper')
    anchor = '    ff_AMediaFormat_setString(format, "mime", codec_mime);\n'
    replacement = '''    if (avctx->codec_id == AV_CODEC_ID_HEVC) {
        ret = aurora_mediacodec_dovi_format(avctx, s, format);
        if (ret < 0)
            goto done;
        if (ret > 0)
            codec_mime = "video/dolby-vision";
    }

''' + anchor
    decoder = _replace(decoder, anchor, replacement, 'MIME selection')
    anchor = 'static const AVOption ff_mediacodec_vdec_options[] = {\n'
    decoder = _replace(decoder, anchor, anchor + '''    { "aurora_dovi", "Request Dolby Vision hardware on a caller-verified native HDR Surface",
            OFFSET(aurora_dovi), AV_OPT_TYPE_BOOL, {.i64 = 0}, 0, 1, VD },
    { "aurora_dovi_profile", "Verified HEVC Dolby profile for an RPU-only stream, zero uses container metadata",
            OFFSET(aurora_dovi_profile), AV_OPT_TYPE_INT, {.i64 = 0}, 0, 10, VD },
''', 'decoder options')
    patched['mediacodecdec.c'] = decoder
    common = patched['mediacodecdec_common.c']
    anchor = '    s->codec_name = ff_AMediaCodecList_getCodecNameByType(mime, profile, 0, avctx);\n'
    common = _replace(common, anchor, '''    if (!strcmp(mime, "video/dolby-vision")) {
        int32_t dovi_profile;
        /* A HEVC Main10 profile number is not an Android Dolby profile. */
        if (!ff_AMediaFormat_getInt32(format, "profile", &dovi_profile) || dovi_profile <= 0)
            return AVERROR_INVALIDDATA;
        s->codec_name = ff_aurora_AMediaCodecList_getExactVideoCodec(mime, dovi_profile, avctx);
        if (!s->codec_name)
            return AVERROR(ENOSYS);
    } else {
''' + anchor + '''    }
''', 'exact Dolby selection')
    patched['mediacodecdec_common.c'] = common
    wrapper = patched['mediacodec_wrapper.c']
    if '/* Aurora hardware selection v2:' not in wrapper:
        raise RuntimeError('Dolby selection requires the hardware selector v2')
    anchor = 'static FFAMediaFormat *mediaformat_jni_newFromObject(void *object)\n'
    wrapper = _replace(wrapper, anchor, '''/* Aurora Dolby profile selection: never relax a DV profile declaration. */
char *ff_aurora_AMediaCodecList_getExactVideoCodec(const char *mime, int profile, void *log_ctx)
{
    AuroraHardwareMimeEvidence evidence = {0};
    aurora_no_hardware_mime_result = 0;
    if (strcmp(mime, "video/dolby-vision") || profile <= 0)
        return NULL;
    return aurora_mediacodec_find_hardware(mime, profile, 0, log_ctx, 0, &evidence);
}

''' + anchor, 'strict profile helper')
    patched['mediacodec_wrapper.c'] = wrapper
    header = patched['mediacodec_wrapper.h']
    anchor = 'char *ff_AMediaCodecList_getCodecNameByType(const char *mime, int profile, int encoder, void *log_ctx);\n'
    header = _replace(header, anchor, anchor +
                       'char *ff_aurora_AMediaCodecList_getExactVideoCodec(const char *mime, int profile, void *log_ctx);\n',
                       'strict profile declaration')
    patched['mediacodec_wrapper.h'] = header
    changed = False
    for name, text in patched.items():
        if text != files[name]:
            (root / name).write_text(text, encoding='utf-8')
            changed = True
    return changed
