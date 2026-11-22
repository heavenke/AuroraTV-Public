"""Observe precise MediaCodec rejections while retaining FFmpeg's error paths."""
from pathlib import Path

MARKER = '/* Aurora codec rejection observations v1.'


def patch_source(text: str) -> str:
    template = Path(__file__).with_suffix('.inc').read_text(encoding='utf-8').rstrip()
    anchors = (
        ('#include "mediacodec_wrapper.h"\n', '#include "mediacodec_wrapper.h"\n\n' + template + '\n'),
        ('    jobject *surface = window ? window->surface : NULL;\n',
         '    jobject *surface = window ? window->surface : NULL;\n    aurora_codec_rejection_reset(ctx);\n'),
        ('    if (ff_jni_exception_check(env, 1, codec) < 0) {\n        ret = AVERROR_EXTERNAL;\n        goto fail;\n    }\n\nfail:\n    return ret;\n}\n\nstatic int mediacodec_jni_start',
         '    aurora_java_codec_rejection(env, ctx, format_ctx, !surface && !crypto && !flags);\n'
         '    if (ff_jni_exception_check(env, 1, codec) < 0) {\n        ret = AVERROR_EXTERNAL;\n        goto fail;\n    }\n\nfail:\n    return ret;\n}\n\nstatic int mediacodec_jni_start'),
        ('    (*env)->CallVoidMethod(env, codec->object, codec->jfields.start_id);\n',
         '    aurora_codec_rejection_reset(ctx);\n    (*env)->CallVoidMethod(env, codec->object, codec->jfields.start_id);\n'
         '    aurora_java_codec_rejection(env, ctx, NULL, 0);\n'),
        ('    ANativeWindow *native_window = NULL;\n',
         '    ANativeWindow *native_window = NULL;\n    aurora_codec_rejection_reset(ctx);\n'),
        ('        status = AMediaCodec_configure(codec->impl, format->impl, native_window, NULL, flags);\n',
         '        status = AMediaCodec_configure(codec->impl, format->impl, native_window, NULL, flags);\n'
         '        aurora_ndk_codec_rejection(ctx, format_ctx, !native_window && !crypto && !flags, status);\n'),
        ('    media_status_t status = AMediaCodec_ ## method (codec->impl);',
         '    aurora_codec_rejection_reset(ctx); \\\n    media_status_t status = AMediaCodec_ ## method (codec->impl);'),
        ('    if (status != AMEDIA_OK) {                                           \\\n        av_log(codec, AV_LOG_ERROR, #method',
         '    if (status != AMEDIA_OK) {                                           \\\n        aurora_ndk_codec_rejection(ctx, NULL, 0, status);                  \\\n        av_log(codec, AV_LOG_ERROR, #method'),
    )
    if MARKER in text:
        legacy = template.replace('int aurora_ffmpeg_codec_rejection(const FFAMediaCodec *codec);\n', '', 1)
        if template not in text and text.count(legacy) == 1:
            text = text.replace(legacy, template, 1)
        if all(text.count(after) == 1 for _, after in anchors): return text
        raise RuntimeError('Partly applied codec rejection observations')
    for before, _ in anchors:
        if text.count(before) != 1:
            raise RuntimeError('Unexpected codec rejection source anchor: ' + before[:80])
    for before, after in anchors: text = text.replace(before, after, 1)
    return text


def apply_codec_rejection_hooks(root: Path) -> None:
    target = root / 'libavcodec/mediacodec_wrapper.c'
    before = target.read_text(encoding='utf-8')
    after = patch_source(before)
    if after != before: target.write_text(after, encoding='utf-8')
