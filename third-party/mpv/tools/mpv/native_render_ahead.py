"""Add an opt-in, bounded render-ahead option to the locked MediaCodec VO.

Default zero preserves the original queue timing and frame-reference limits.
Only preinit queue scheduling changes: draw/flip, media PTS, decoder selection,
pixel geometry and every other VO remain unchanged. This helper does not build.
All anchors and postconditions are validated before writing the single target.

Use vo=mediacodec_embed plus the separate per-instance option
vo-mediacodec-embed-render-ahead=0.020. The locked mpv option parser rejects
colon suboptions in the vo string; this patch does not change that parser.
"""
from __future__ import annotations

import argparse
from pathlib import Path

_MARKER = '/* Aurora optional native render-ahead v1.'
_TARGET = 'video/out/vo_mediacodec_embed.c'


def _edits() -> tuple[tuple[str, str, str], ...]:
    return (
        ('option and timer headers', '#include "common/common.h"\n#include "vo.h"\n',
         '#include "common/common.h"\n#include "options/m_option.h"\n#include "osdep/timer.h"\n#include "vo.h"\n'),
        ('private option storage', '    struct mp_image *next_image;\n    struct mp_hwdec_ctx hwctx;\n',
         '    struct mp_image *next_image;\n    double render_ahead;\n    struct mp_hwdec_ctx hwctx;\n'),
        ('native queue timing', '    hwdec_devices_add(vo->hwdec_devs, &p->hwctx);\n    return 0;\n',
         '    hwdec_devices_add(vo->hwdec_devs, &p->hwctx);\n'
         '    /* Aurora optional native render-ahead v1. Seconds; zero retains the\n'
         '     * default timing. This advances flip submission, not media PTS. */\n'
         '    vo_set_queue_params(vo, MP_TIME_S_TO_NS(p->render_ahead), 1, 2);\n'
         '    return 0;\n'),
        ('option base type', 'const struct vo_driver video_out_mediacodec_embed = {\n',
         '#define OPT_BASE_STRUCT struct priv\n\nconst struct vo_driver video_out_mediacodec_embed = {\n'),
        ('bounded VO suboption', '    .priv_size = sizeof(struct priv),\n};\n',
         '    .priv_size = sizeof(struct priv),\n'
         '    .options = (const struct m_option []) {\n'
         '        {"render-ahead", OPT_DOUBLE(render_ahead), M_RANGE(0, 0.1), OPTDEF_DOUBLE(0)},\n'
         '        {0},\n'
         '    },\n'
         '    .options_prefix = "vo-mediacodec-embed",\n'
         '};\n'),
    )


def _verify(source: str, edits: tuple[tuple[str, str, str], ...]) -> None:
    if source.count(_MARKER) != 1:
        raise RuntimeError('Altered native render-ahead declaration')
    for label, before, after in edits:
        expected_old = 1 + sum(new.count(before) - old.count(before) for _, old, new in edits)
        if source.count(after) != 1 or source.count(before) != expected_old:
            raise RuntimeError('Native render-ahead postcondition failed: ' + label)


def patch_source(source: str) -> str:
    """Patch one known VO source, or verify an exact already-patched version."""
    edits = _edits()
    applied = [source.count(after) == 1 for _, _, after in edits]
    if all(applied):
        _verify(source, edits)
        return source
    if any(applied) or _MARKER in source or 'render_ahead' in source or '"render-ahead"' in source:
        raise RuntimeError('Partly applied or altered native render-ahead patch')
    for label, before, _ in edits:
        if source.count(before) != 1:
            raise RuntimeError('Unexpected MediaCodec VO anchor: ' + label)
    result = source
    for _, before, after in edits:
        result = result.replace(before, after, 1)
    _verify(result, edits)
    return result


def apply_native_render_ahead(mpv_source: Path) -> bool:
    """Patch only the MediaCodec VO; return False without writing if unchanged."""
    target = Path(mpv_source) / _TARGET
    before = target.read_text(encoding='utf-8')
    after = patch_source(before)
    if after == before:
        return False
    target.write_text(after, encoding='utf-8')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mpv_source', type=Path)
    args = parser.parse_args()
    print('patched' if apply_native_render_ahead(args.mpv_source) else 'unchanged')
