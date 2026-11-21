"""Expose demuxed transfer/primaries in track-list before decoder initialization.

Only real codec color metadata is reported. Bit depth, codec profile, filename,
device model and network probing are deliberately not used to infer HDR.
"""
from pathlib import Path


ANCHOR = '''        {"demux-h",     SUB_PROP_INT(p.disp_h), .unavailable = !p.disp_h},
'''
LEGACY_PROPERTIES = '''        /* Aurora demux color metadata: readable during on_preloaded. */
        {"demux-gamma",
            SUB_PROP_STR(m_opt_choice_str(pl_csp_trc_names, p.color.transfer)),
                        .unavailable = !p.color.transfer},
        {"demux-primaries",
            SUB_PROP_STR(m_opt_choice_str(pl_csp_prim_names, p.color.primaries)),
                        .unavailable = !p.color.primaries},
'''
PROPERTIES = LEGACY_PROPERTIES.replace('p.color.', 'demux_color.')
INCLUDE_ANCHOR = '#include <libavutil/avstring.h>\n'
INCLUDES = '#include <libavcodec/codec_par.h>\n#include <libplacebo/utils/libav.h>\n' + INCLUDE_ANCHOR
LOCAL_ANCHOR = '    bool has_crop = mp_rect_w(p.crop) > 0 && mp_rect_h(p.crop) > 0;\n'
LOCAL_COLOR = '''    /* Private demuxers may populate p.color directly; lavf retains AVCodecParameters.
     * Report the real headers without mutating the decoder's color defaults. */
    struct pl_color_space demux_color = p.color;
    if (p.lav_codecpar) {
        if (!demux_color.transfer)
            demux_color.transfer = pl_transfer_from_av(p.lav_codecpar->color_trc);
        if (!demux_color.primaries)
            demux_color.primaries = pl_primaries_from_av(p.lav_codecpar->color_primaries);
    }

'''


def apply_hdr_metadata(mpv_source: Path) -> bool:
    path = Path(mpv_source) / 'player/command.c'
    original = path.read_text(encoding='utf-8')
    if PROPERTIES in original:
        if (original.count(PROPERTIES) != 1 or original.count(ANCHOR) != 1 or
                original.count(INCLUDES) != 1 or original.count(LOCAL_COLOR) != 1):
            raise RuntimeError('Duplicate HDR metadata properties')
        return False
    legacy = LEGACY_PROPERTIES in original
    if not legacy and ('Aurora demux color metadata' in original or '"demux-gamma"' in original):
        raise RuntimeError('Changed HDR metadata properties in already patched source')
    if (original.count(ANCHOR) != 1 or original.count(INCLUDE_ANCHOR) != 1 or
            original.count(LOCAL_ANCHOR) != 1 or (legacy and original.count(LEGACY_PROPERTIES) != 1)):
        raise RuntimeError('Unexpected track-list HDR metadata source')
    patched = original.replace(INCLUDE_ANCHOR, INCLUDES, 1).replace(LOCAL_ANCHOR, LOCAL_COLOR + LOCAL_ANCHOR, 1)
    patched = patched.replace(LEGACY_PROPERTIES, PROPERTIES, 1) if legacy else patched.replace(ANCHOR, ANCHOR + PROPERTIES, 1)
    path.write_text(patched, encoding='utf-8')
    return True
