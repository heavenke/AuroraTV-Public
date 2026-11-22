"""Apply the bounded hardware-only MediaCodec selection patch to FFmpeg.

Usage: apply_hardware_codec_selection(Path('/path/to/ffmpeg'))
The patch touches only mediacodec_wrapper.c. All anchors are checked before any
write; an unexpected or partly applied source is rejected rather than guessed.
Android API 21-28 retain their exact-profile path. The declaration-relaxed path
requires positive isHardwareAccelerated() evidence available on API 29+.
The optional TLS getter reports a definite missing hardware video MIME only
after complete successful enumeration, never a profile or size mismatch.
"""

from __future__ import annotations

import argparse
from pathlib import Path


_LEGACY_WRAPPER = '''/* Aurora hardware selection v1: public capability declarations are hints.
 * Preserve exact-profile preference. A relaxed retry only accepts a decoder
 * positively identified as hardware by the public Android API (API 29+).
 * This changes selection only: stream profile, configure/start failures, and
 * real decoded/rendered-frame checks retain their original meaning.
 */
char *ff_AMediaCodecList_getCodecNameByType(const char *mime, int profile, int encoder, void *log_ctx)
{
    char *name = aurora_mediacodec_find_hardware(mime, profile, encoder, log_ctx, 0);

    if (!name && !encoder && profile >= 0 && !av_strncasecmp(mime, "video/", 6)) {
        name = aurora_mediacodec_find_hardware(mime, -1, encoder, log_ctx, 1);
        if (name)
            av_log(log_ctx, AV_LOG_VERBOSE,
                   "Hardware video decoder selected without a declared profile match; "
                   "configuration and decoded output must still succeed.\\n");
    }

    return name;
}'''
_V2_MARKER = '/* Aurora hardware selection v2:'
_EVIDENCE_MARKER = '/* Aurora selection enumeration evidence v2. */'


def _edits() -> tuple[tuple[str, str, str], ...]:
    # Keep the exact v1 recipe so already-patched build caches can be verified
    # and migrated without silently accepting partial or externally edited code.
    wrapper = _LEGACY_WRAPPER
    software_check = '''        if (jfields.is_software_only_id) {
            int is_software_only = (*env)->CallBooleanMethod(env, info, jfields.is_software_only_id);
            if (ff_jni_exception_check(env, 1, log_ctx) < 0) {
                goto done;
            }

            if (is_software_only) {
                goto done_with_info;
            }
        }
'''
    hardware_check = '''
        /* A relaxed profile search must never infer hardware from a vendor name. */
        if (!encoder && !av_strncasecmp(mime, "video/", 6) &&
            jfields.is_hardware_accelerated_id) {
            int hardware = (*env)->CallBooleanMethod(env, info, jfields.is_hardware_accelerated_id);
            if (ff_jni_exception_check(env, 1, log_ctx) < 0)
                goto done;
            if (!hardware)
                goto done_with_info;
        } else if (require_hardware) {
            /* API 21-28 have no public positive hardware classification. */
            goto done_with_info;
        }
'''
    capability_anchor = '''            profile_levels = (*env)->GetObjectField(env, capabilities, jfields.profile_levels_id);
'''
    required_features = '''            /* A clear ordinary Surface is neither secure nor tunneled output. */
            if (!encoder && !av_strncasecmp(mime, "video/", 6)) {
                static const char *const required_features[] = {
                    "secure-playback", "tunneled-playback"
                };
                int feature_index;
                if (!jfields.is_feature_required_id) {
                    if (require_hardware)
                        goto done_with_type;
                } else for (feature_index = 0;
                            feature_index < FF_ARRAY_ELEMS(required_features); feature_index++) {
                    jstring feature = (*env)->NewStringUTF(env, required_features[feature_index]);
                    int required;
                    if (!feature)
                        goto done;
                    required = (*env)->CallBooleanMethod(env, capabilities,
                                                        jfields.is_feature_required_id, feature);
                    (*env)->DeleteLocalRef(env, feature);
                    if (ff_jni_exception_check(env, 1, log_ctx) < 0)
                        goto done;
                    if (required)
                        goto done_with_type;
                }
            }

'''
    method_anchor = '        { "android/media/MediaCodecInfo", "isSoftwareOnly", "()Z", FF_JNI_METHOD, OFFSET(is_software_only_id), 0 },\n'
    caps_anchor = '    { "android/media/MediaCodecInfo$CodecCapabilities", NULL, NULL, FF_JNI_CLASS, OFFSET(codec_capabilities_class), 1 },\n'
    signature = 'char *ff_AMediaCodecList_getCodecNameByType(const char *mime, int profile, int encoder, void *log_ctx)\n'
    return (
        ('hardware JNI field', '    jmethodID is_software_only_id;\n',
         '    jmethodID is_software_only_id;\n    jmethodID is_hardware_accelerated_id;\n'),
        ('feature JNI field', '    jclass codec_capabilities_class;\n',
         '    jclass codec_capabilities_class;\n    jmethodID is_feature_required_id;\n'),
        ('hardware JNI mapping', method_anchor, method_anchor +
         '        { "android/media/MediaCodecInfo", "isHardwareAccelerated", "()Z", FF_JNI_METHOD, OFFSET(is_hardware_accelerated_id), 0 },\n'),
        ('feature JNI mapping', caps_anchor, caps_anchor +
         '        { "android/media/MediaCodecInfo$CodecCapabilities", "isFeatureRequired", "(Ljava/lang/String;)Z", FF_JNI_METHOD, OFFSET(is_feature_required_id), 0 },\n'),
        ('selection signature', signature,
         'static char *aurora_mediacodec_find_hardware(const char *mime, int profile, int encoder,\n'
         '                                           void *log_ctx, int require_hardware)\n'),
        ('positive hardware check', software_check, software_check + hardware_check),
        ('standard software/secure exclusions', '        /* Skip software decoders */\n        if (\n',
         '        /* Skip software and secure-only components, including standard C2 software names. */\n'
         '        if (\n'
         '            !av_strncasecmp(name, "c2.android.", 11) ||\n'
         '            !av_strncasecmp(name, "c2.google.", 10) ||\n'
         '            (strlen(name) >= 7 && !av_strcasecmp(name + strlen(name) - 7, ".secure")) ||\n'),
        ('required output features', capability_anchor, required_features + capability_anchor),
        ('exact then relaxed wrapper', 'static FFAMediaFormat *mediaformat_jni_new(void)\n',
         wrapper + '\n\nstatic FFAMediaFormat *mediaformat_jni_new(void)\n'),
    )


def _apply_edits(source: str, edits: tuple[tuple[str, str, str], ...], marker: str) -> str:
    # The replacement often contains its own original anchor. Inspect complete
    # replacement blocks first so a second application remains byte-identical.
    applied = [source.count(after) == 1 for _, _, after in edits]
    if all(applied):
        _verify_patched(source, edits)
        return source
    if any(applied) or marker in source:
        raise RuntimeError('Partly applied or altered hardware codec selection patch')
    for label, before, _ in edits:
        count = source.count(before)
        if count != 1:
            raise RuntimeError(f'Unexpected FFmpeg {label} anchor count: {count}')
    result = source
    for _, before, after in edits:
        result = result.replace(before, after, 1)
    _verify_patched(result, edits)
    return result


def _result_edits() -> tuple[tuple[str, str, str], ...]:
    wrapper = Path(__file__).with_suffix('.inc').read_text(encoding='utf-8').rstrip()
    if wrapper.count(_V2_MARKER) != 1:
        raise RuntimeError('Unexpected hardware codec selection v2 template')
    signature = '''static char *aurora_mediacodec_find_hardware(const char *mime, int profile, int encoder,
                                           void *log_ctx, int require_hardware)
'''
    evidence_signature = '''/* Aurora selection enumeration evidence v2. */
typedef struct AuroraHardwareMimeEvidence {
    int complete;
    int mime_candidate;
    int uncertain;
} AuroraHardwareMimeEvidence;

static char *aurora_mediacodec_find_hardware(const char *mime, int profile, int encoder,
                                           void *log_ctx, int require_hardware,
                                           AuroraHardwareMimeEvidence *evidence)
'''
    env = '    JNI_GET_ENV_OR_RETURN(env, log_ctx, NULL);\n'
    returned_types = '''        types = (*env)->CallObjectMethod(env, info, jfields.get_supported_types_id);
        if (ff_jni_exception_check(env, 1, log_ctx) < 0) {
            goto done;
        }
'''
    types = '        type_count = (*env)->GetArrayLength(env, types);\n'
    profiles = '            profile_count = (*env)->GetArrayLength(env, profile_levels);\n'
    missing_features = '                if (!jfields.is_feature_required_id) {\n'
    candidate = '            profile_levels = (*env)->GetObjectField(env, capabilities, jfields.profile_levels_id);\n'
    completion = '''        av_freep(&name);
    }

done:
'''
    return_anchor = '''    if (!found_codec) {
        av_freep(&name);
    }

    return name;
'''
    return (
        ('enumeration evidence type', signature, evidence_signature),
        ('reset scan evidence', env,
         '    *evidence = (AuroraHardwareMimeEvidence){0};\n\n' + env),
        ('null returned type array evidence', returned_types, returned_types +
         '        if (!types)\n            evidence->uncertain = 1;\n'),
        ('type array evidence', types, types +
         '        if (!types || type_count < 0 || (*env)->ExceptionCheck(env))\n'
         '            evidence->uncertain = 1;\n'),
        ('profile array evidence', profiles, profiles +
         '            if (!profile_levels || profile_count < 0 || (*env)->ExceptionCheck(env))\n'
         '                evidence->uncertain = 1;\n'),
        ('unknown required features evidence', missing_features, missing_features +
         '                    evidence->uncertain = 1;\n'),
        ('MIME before profile evidence', candidate,
         '            /* Eligible aliases/unknown legacy implementations also suppress a hard rejection. */\n'
         '            evidence->mime_candidate = 1;\n\n' + candidate),
        ('full enumeration evidence', completion, completion.replace('done:\n',
         '    evidence->complete = i == codec_count && !evidence->uncertain &&\n'
         '                         !(*env)->ExceptionCheck(env);\n\n'
         'done:\n')),
        ('cleanup exception evidence', return_anchor,
         '    if ((*env)->ExceptionCheck(env))\n        evidence->uncertain = 1;\n\n' + return_anchor),
        ('TLS result wrapper', _LEGACY_WRAPPER, wrapper),
    )


def _selection_region(source: str) -> tuple[int, int]:
    end = 'static FFAMediaFormat *mediaformat_jni_new(void)\n'
    old_start = 'static char *aurora_mediacodec_find_hardware('
    start_marker = _EVIDENCE_MARKER if _EVIDENCE_MARKER in source else old_start
    if source.count(start_marker) != 1 or source.count(end) != 1:
        raise RuntimeError('Unexpected hardware selection region boundaries')
    start, finish = source.index(start_marker), source.index(end)
    if start >= finish:
        raise RuntimeError('Reversed hardware selection region boundaries')
    return start, finish


def patch_source(source: str) -> str:
    """Apply raw/v1 -> v2, or verify v2 without changing any selection result."""
    base_edits, result_edits = _edits(), _result_edits()
    if _V2_MARKER in source or _EVIDENCE_MARKER in source:
        start, finish = _selection_region(source)
        block = source[start:finish]
        # An early complete v2 build predates the null-array check before the
        # software/encoder skip. Accept only that exact known revision: the
        # restored block must pass every other v2 and reversible v1 invariant.
        _, early_before, final_after = next(edit for edit in result_edits
                                            if edit[0] == 'null returned type array evidence')
        if block.count(final_after) == 0 and block.count(early_before) == 1:
            block = block.replace(early_before, final_after, 1)
        _verify_patched(block, result_edits)
        # Verify a reversible, exact v1 source underneath the new observations.
        legacy = block
        for _, before, after in reversed(result_edits):
            legacy = legacy.replace(after, before, 1)
        _verify_patched(source[:start] + legacy + source[finish:], base_edits)
        return source[:start] + block + source[finish:]
    legacy = _apply_edits(source, base_edits, '/* Aurora hardware selection v1:')
    start, finish = _selection_region(legacy)
    upgraded = _apply_edits(legacy[start:finish], result_edits, _V2_MARKER)
    return legacy[:start] + upgraded + legacy[finish:]


def _verify_patched(source: str, edits: tuple[tuple[str, str, str], ...]) -> None:
    for label, before, after in edits:
        # Some replacement blocks deliberately retain their old anchor. Also
        # account for the public signature reintroduced by the outer wrapper.
        expected_old = 1 + sum(new.count(before) - old.count(before) for _, old, new in edits)
        if source.count(after) != 1 or source.count(before) != expected_old:
            raise RuntimeError(f'Hardware codec selection patch postcondition failed: {label}')


def apply_hardware_codec_selection(ffmpeg_source: Path) -> bool:
    """Patch an FFmpeg source root. Return True only when the file changed."""
    target = Path(ffmpeg_source) / 'libavcodec' / 'mediacodec_wrapper.c'
    original = target.read_text(encoding='utf-8')
    patched = patch_source(original)
    if patched == original:
        return False
    target.write_text(patched, encoding='utf-8')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ffmpeg_source', type=Path)
    args = parser.parse_args()
    print('patched' if apply_hardware_codec_selection(args.ffmpeg_source) else 'unchanged')
