"""Apply MediaCodec-specific HEVC transfer-characteristic handling to locked FFmpeg.

The new BSF option defaults off. Only the HEVC MediaCodec decoder's existing
Annex-B filter chain enables it. CBS deletes individual invalid messages and
performs RBSP/EBSP serialization. The decoder can repeat a proven HLG declaration
within its coded layer video sequence. No channel or device names are used.
All source anchors are validated before writes. Call only on an owned source
tree; this module never locates or alters a global build cache itself.
"""

from __future__ import annotations

from pathlib import Path
import hashlib

# Exact previously validated transactional helper, before the CENC early-pass guard.
CENC_FILTER_SHA256 = 'eff9f707b9d2af7e38496ccda318032f91697d28259c519a00123ceae89ec85f'
LEGACY_FILTER_SHA256 = '26638ab6d099316b08591300df9e63596b17a9778aa4648b2fad0983a6d192fb'


def patch_sources(sources: dict[str, str]) -> dict[str, str]:
    edits = {
        'libavcodec/cbs_sei.c': (
            ('static void cbs_sei_delete_message(SEIRawMessageList *list,',
             'void ff_cbs_sei_delete_message(SEIRawMessageList *list,'),
            ('                cbs_sei_delete_message(list, j);',
             '                ff_cbs_sei_delete_message(list, j);'),
        ),
        'libavcodec/cbs_sei.h': (
            ('void ff_cbs_sei_delete_message_type(CodedBitstreamContext *ctx,',
             '/* Delete one message with normal CBS reference cleanup. */\n'
             'void ff_cbs_sei_delete_message(SEIRawMessageList *list, int position);\n\n'
             'void ff_cbs_sei_delete_message_type(CodedBitstreamContext *ctx,'),
        ),
        'libavcodec/bsf/h265_metadata.c': (
            ('#include "libavutil/opt.h"\n',
             '#include "libavutil/opt.h"\n#include "libavutil/pixdesc.h"\n'),
            ('enum {\n    LEVEL_UNSET = -2,',
             '#include "aurora_hevc_invalid_atc.inc"\n\nenum {\n    LEVEL_UNSET = -2,'),
            ('    int aud;\n', '    int aud;\n    int remove_invalid_atc;\n'),
            ('} H265MetadataContext;\n',
             '} H265MetadataContext;\n\n#include "aurora_hevc_invalid_atc_filter.inc"\n'),
            ('    // If an AUD is present, it must be the first NAL unit.\n',
             '    if (ctx->remove_invalid_atc)\n        aurora_hevc_remove_invalid_atc(au);\n\n'
             '    // If an AUD is present, it must be the first NAL unit.\n'),
            ('static const AVOption h265_metadata_options[] = {\n',
             'static const AVOption h265_metadata_options[] = {\n'
             '    { "remove_invalid_atc", "Remove only reserved or undefined alternative transfer values",\n'
             '      OFFSET(remove_invalid_atc), AV_OPT_TYPE_BOOL, { .i64 = 0 }, 0, 1, FLAGS },\n'),
            ('    return ff_cbs_bsf_generic_init(bsf, &h265_metadata_type);',
             '    H265MetadataContext *ctx = bsf->priv_data;\n'
             '    if (aurora_hevc_sanitize_only(ctx))\n        return aurora_hevc_sanitize_init(bsf);\n'
             '    return ff_cbs_bsf_generic_init(bsf, &h265_metadata_type);'),
            ('    .filter         = &ff_cbs_bsf_generic_filter,',
             '    .filter         = &aurora_hevc_metadata_filter,'),
        ),
        'libavcodec/mediacodecdec.c': (
            ('DECLARE_MEDIACODEC_VDEC(hevc, "H.265", AV_CODEC_ID_HEVC, "hevc_mp4toannexb")',
             'DECLARE_MEDIACODEC_VDEC(hevc, "H.265", AV_CODEC_ID_HEVC, "hevc_mp4toannexb,hevc_metadata=remove_invalid_atc=1")'),
        ),
        'configure': (
            ('hevc_mediacodec_decoder_select="hevc_mp4toannexb_bsf hevc_parser"',
             'hevc_mediacodec_decoder_select="hevc_mp4toannexb_bsf hevc_metadata_bsf hevc_parser"'),
        ),
    }
    if set(sources) != set(edits):
        raise RuntimeError('Unexpected HEVC ATC source set')
    state = [(path, before, after, sources[path].count(after) == 1)
             for path, changes in edits.items() for before, after in changes]
    def verify(values: dict[str, str]) -> None:
        for path, changes in edits.items():
            for before, after in changes:
                expected_old = 1 + sum(new.count(before) - old.count(before) for old, new in changes)
                if values[path].count(after) != 1 or values[path].count(before) != expected_old:
                    raise RuntimeError(f'HEVC ATC patch postcondition failed: {path}')
    if all(applied for _, _, _, applied in state):
        verify(sources)
        return dict(sources)
    if any(applied for _, _, _, applied in state):
        raise RuntimeError('Partly applied or altered HEVC ATC patch')
    for path, before, _, _ in state:
        if sources[path].count(before) != 1:
            raise RuntimeError(f'Unexpected HEVC ATC source anchor: {path}')
    result = dict(sources)
    for path, before, after, _ in state:
        result[path] = result[path].replace(before, after, 1)
    verify(result)
    return result


# Accept the verified v1 source anchors in existing build trees as well as the
# upstream files. Validate the HLG extension as a unit before patching either.
HLG_EDITS = (
    ('    int crop_bottom;', '    int crop_bottom;\n    int hlg_pps_plus_one;'),
    ('static const AVOption h265_metadata_options[] = {',
     '#include "aurora_hevc_hlg_atc.inc"\n\nstatic const AVOption h265_metadata_options[] = {'),
    ('    .close          = &ff_cbs_bsf_generic_close,',
     '    .flush          = &aurora_hevc_hlg_flush,\n    .close          = &ff_cbs_bsf_generic_close,'),
)


def apply_hevc_invalid_atc(ffmpeg_source: Path) -> bool:
    paths = ('libavcodec/cbs_sei.c', 'libavcodec/cbs_sei.h',
             'libavcodec/bsf/h265_metadata.c', 'libavcodec/mediacodecdec.c', 'configure')
    original = {name: (ffmpeg_source / name).read_text(encoding='utf-8') for name in paths}
    metadata = 'libavcodec/bsf/h265_metadata.c'
    base = dict(original)
    markers = [base[metadata].count(new) for _, new in HLG_EDITS]
    if any(markers):
        if markers != [1] * len(HLG_EDITS):
            raise RuntimeError('Incomplete HLG ATC patch')
        for old, new in HLG_EDITS:
            base[metadata] = base[metadata].replace(new, old, 1)
    patched = patch_sources(base)
    for old, new in HLG_EDITS:
        if patched[metadata].count(old) != 1:
            raise RuntimeError('Unexpected HLG ATC anchor')
        patched[metadata] = patched[metadata].replace(old, new, 1)
    templates = {
        'aurora_hevc_invalid_atc.inc': Path(__file__).with_suffix('.inc').read_text(encoding='utf-8'),
        'aurora_hevc_invalid_atc_filter.inc': Path(__file__).with_name('hevc_invalid_atc_filter.inc').read_text(encoding='utf-8'),
    }
    templates['aurora_hevc_hlg_atc.inc'] = Path(__file__).with_name('hevc_hlg_atc.inc').read_text(encoding='utf-8')
    pending_helpers = {}
    for name, template in templates.items():
        helper = ffmpeg_source / 'libavcodec/bsf' / name
        if helper.exists():
            existing = helper.read_text(encoding='utf-8')
            if existing == template:
                continue
            known_legacy = name == 'aurora_hevc_invalid_atc_filter.inc' and \
                hashlib.sha256(existing.encode('utf-8')).hexdigest() in {LEGACY_FILTER_SHA256, CENC_FILTER_SHA256}
            if not known_legacy:
                raise RuntimeError('Altered HEVC ATC helper')
        pending_helpers[name] = template
    changed = patched != original or bool(pending_helpers)
    if not changed:
        return False
    for name in paths:
        if patched[name] != original[name]:
            (ffmpeg_source / name).write_text(patched[name], encoding='utf-8')
    for name, template in pending_helpers.items():
        (ffmpeg_source / 'libavcodec/bsf' / name).write_text(template, encoding='utf-8')
    return True
