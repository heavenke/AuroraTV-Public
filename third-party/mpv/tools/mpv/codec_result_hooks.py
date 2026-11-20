"""Patch FFmpeg's MediaCodec video initialization with optional numeric results.

The FFmpeg context must already provide immutable int64_t aurora_client and
aurora_epoch fields. This helper only changes mediacodecdec_common.c and leaves
the existing started observer and decoder cleanup untouched. Failure to match
every expected source anchor aborts before a write, including partial patches.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


_START = 'int ff_mediacodec_dec_init(AVCodecContext *avctx, MediaCodecDecContext *s,\n'
_END = 'int ff_mediacodec_dec_send(AVCodecContext *avctx, MediaCodecDecContext *s,\n'
_MARKER = '/* Aurora structured video codec lifecycle'


def _edits() -> tuple[tuple[str, str, str], ...]:
    template = Path(__file__).with_suffix('.inc').read_text(encoding='utf-8').rstrip()
    if template.count(_MARKER) != 1:
        raise RuntimeError('Unexpected codec result hook template')
    begin = '    s->current_input_buffer = -1;\n'
    selection = '    if (ret < 0)\n        goto fail;\n'
    configure = '''        av_freep(&desc);

        ret = AVERROR_EXTERNAL;
        goto fail;
'''
    start = '''        av_freep(&desc);
        ret = AVERROR_EXTERNAL;
        goto fail;
'''
    context = '''                    "Failed to configure context\\n");
                goto fail;
'''
    success = '    av_log(avctx, AV_LOG_DEBUG, "MediaCodec %p started successfully\\n", s->codec);\n'
    return (
        ('observer declaration', _START, template + '\n\n' + _START),
        ('initialization begin', begin, begin + '    aurora_mediacodec_report_result(avctx, s, mime, 0, 0);\n'),
        ('selection failure', selection, '    if (ret < 0) {\n'
         '        aurora_mediacodec_report_result(avctx, s, mime, 1, ret);\n'
         '        goto fail;\n    }\n'),
        ('configure failure', configure, configure.replace('        goto fail;\n',
         '        aurora_mediacodec_report_result(avctx, s, mime, 2, status);\n        goto fail;\n')),
        ('start failure', start, start.replace('        goto fail;\n',
         '        aurora_mediacodec_report_result(avctx, s, mime, 3, status);\n        goto fail;\n')),
        ('output context failure', context, context.replace('                goto fail;\n',
         '                /* Stage 2 also covers output-format parsing after start.\n'
         '                 * Here code is the FFmpeg parse error, not a platform status. */\n'
         '                aurora_mediacodec_report_result(avctx, s, mime, 2, ret);\n                goto fail;\n')),
        ('successful initialization', success,
         '    aurora_mediacodec_report_result(avctx, s, mime, 4, 0);\n\n' + success),
    )


def _verify(block: str, edits: tuple[tuple[str, str, str], ...]) -> None:
    for label, before, after in edits:
        expected_old = 1 + sum(new.count(before) - old.count(before) for _, old, new in edits)
        if block.count(after) != 1 or block.count(before) != expected_old:
            raise RuntimeError(f'Codec result hook postcondition failed: {label}')


def patch_source(source: str) -> str:
    """Patch only the initialization function and an adjacent weak helper."""
    if source.count(_START) != 1 or source.count(_END) != 1:
        raise RuntimeError('Unexpected MediaCodec initialization function boundaries')
    start = source.index(_START)
    end = source.index(_END)
    if start >= end:
        raise RuntimeError('Reversed MediaCodec initialization function boundaries')
    if _MARKER in source:
        if source.count(_MARKER) != 1 or source.index(_MARKER) > start:
            raise RuntimeError('Altered codec result hook declaration')
        start = source.index(_MARKER)
        legacy = source[start:source.index(_START)].strip()
        if hashlib.sha256(legacy.encode()).hexdigest() == '04c812b42aac528928939dd177b0a16c4e033dba0c544a757356745ef6f1c5d4':
            replacement = Path(__file__).with_suffix('.inc').read_text(encoding='utf-8').rstrip()
            source = source[:start] + replacement + '\n\n' + source[source.index(_START):]
            end = source.index(_END)
    block = source[start:end]
    edits = _edits()
    applied = [block.count(after) == 1 for _, _, after in edits]
    if all(applied):
        _verify(block, edits)
        return source
    if any(applied) or _MARKER in source:
        raise RuntimeError('Partly applied or altered codec result hooks')
    for label, before, _ in edits:
        count = block.count(before)
        if count != 1:
            raise RuntimeError(f'Unexpected FFmpeg {label} anchor count: {count}')
    for _, before, after in edits:
        block = block.replace(before, after, 1)
    _verify(block, edits)
    return source[:start] + block + source[end:]


def apply_codec_result_hooks(ffmpeg_source: Path) -> bool:
    """Patch an FFmpeg source root; return True only when its source changed."""
    target = Path(ffmpeg_source) / 'libavcodec' / 'mediacodecdec_common.c'
    original = target.read_text(encoding='utf-8')
    patched = patch_source(original)
    if original == patched:
        return False
    target.write_text(patched, encoding='utf-8')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ffmpeg_source', type=Path)
    args = parser.parse_args()
    print('patched' if apply_codec_result_hooks(args.ffmpeg_source) else 'unchanged')
