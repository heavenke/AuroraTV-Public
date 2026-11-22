"""Add optional bounded MediaCodec stage observations to locked FFmpeg sources.

Both source files are fully checked before either is written. The original
codec calls, arguments, result values, branches, and cleanup remain unchanged.
The Core observer may return zero to disable observations without clock/JNI
work in this patch. This module never builds or accesses a device.
"""

from __future__ import annotations

import argparse
from pathlib import Path


_SHARED_MARKER = '/* Aurora optional codec stage hooks v1.'
_RECEIVE_SIGNATURE = 'static int mediacodec_receive_frame(AVCodecContext *avctx, AVFrame *frame)\n'
_COMMON_SIGNATURE = 'int ff_mediacodec_dec_send(AVCodecContext *avctx, MediaCodecDecContext *s,\n'


def _section(name: str) -> str:
    text = Path(__file__).with_suffix('.inc').read_text(encoding='utf-8')
    begin, end = f'/* AURORA_STAGE_{name}_BEGIN */', f'/* AURORA_STAGE_{name}_END */'
    if text.count(begin) != 1 or text.count(end) != 1:
        raise RuntimeError(f'Unexpected codec stage template section: {name}')
    start, finish = text.index(begin) + len(begin), text.index(end)
    if start >= finish:
        raise RuntimeError(f'Reversed codec stage template section: {name}')
    return text[start:finish].strip() + '\n\n'


def _observed_call(label: str, original: str, owner: str, stage: int,
                   result: str, pts: str = 'AV_NOPTS_VALUE', size: str = '0') -> tuple[str, str, str]:
    indentation = original[:len(original) - len(original.lstrip(' '))]
    inner = indentation + '    '
    replacement = (indentation + '{\n' +
        inner + f'const int64_t stage_client = {owner}->aurora_client;\n' +
        inner + f'const int64_t stage_epoch = {owner}->aurora_epoch;\n' +
        inner + f'int64_t stage_start_us = aurora_codec_stage_start(avctx, stage_client, stage_epoch, {stage});\n' +
        inner + original.strip() + '\n' +
        inner + f'aurora_codec_stage_finish(stage_client, stage_epoch, {stage}, stage_start_us,\n' +
        inner + f'                          {result}, {pts}, {size});\n' +
        indentation + '}\n')
    return label, original, replacement


def _edits(name: str) -> tuple[tuple[str, str, str], ...]:
    shared = _section('SHARED')
    if name == 'mediacodecdec.c':
        return (
            ('receive implementation name and helpers', _RECEIVE_SIGNATURE,
             shared + _RECEIVE_SIGNATURE.replace('mediacodec_receive_frame(', 'aurora_mediacodec_receive_frame_internal(')),
            _observed_call('outer input dequeue',
                '            index = ff_AMediaCodec_dequeueInputBuffer(s->ctx->codec, 0);\n',
                's', 0, '(int)index'),
            ('receive wrapper', 'static void mediacodec_decode_flush(AVCodecContext *avctx)\n',
             _section('RECEIVE') + 'static void mediacodec_decode_flush(AVCodecContext *avctx)\n'),
        )
    if name == 'mediacodecdec_common.c':
        return (
            ('shared common helpers', _COMMON_SIGNATURE, shared + _COMMON_SIGNATURE),
            _observed_call('inner input dequeue',
                '            index = ff_AMediaCodec_dequeueInputBuffer(codec, input_dequeue_timeout_us);\n',
                's', 0, '(int)index'),
            _observed_call('output dequeue',
                '    index = ff_AMediaCodec_dequeueOutputBuffer(codec, &info, output_dequeue_timeout_us);\n',
                's', 1, '(int)index', 'index >= 0 ? info.presentationTimeUs : AV_NOPTS_VALUE',
                'index >= 0 ? info.size : 0'),
            _observed_call('EOS input queue',
                '            status = ff_AMediaCodec_queueInputBuffer(codec, index, 0, 0, pts, flags);\n',
                's', 2, 'status', 'pts'),
            _observed_call('data input queue',
                '        status = ff_AMediaCodec_queueInputBuffer(codec, index, 0, size, pts, 0);\n',
                's', 2, 'status', 'pts', '(int64_t)size'),
        )
    raise ValueError(f'Unsupported MediaCodec source: {name}')


def _verify(source: str, edits: tuple[tuple[str, str, str], ...]) -> None:
    for label, before, after in edits:
        expected_old = 1 + sum(new.count(before) - old.count(before) for _, old, new in edits)
        if source.count(after) != 1 or source.count(before) != expected_old:
            raise RuntimeError(f'Codec stage patch postcondition failed: {label}')


def patch_source(name: str, source: str) -> str:
    """Patch a known source or verify an exact already-patched version."""
    edits = _edits(name)
    applied = [source.count(after) == 1 for _, _, after in edits]
    if all(applied):
        _verify(source, edits)
        return source
    if any(applied) or _SHARED_MARKER in source or '/* Aurora receive-frame stage wrapper v1.' in source:
        raise RuntimeError(f'Partly applied or altered codec stage patch: {name}')
    for label, before, _ in edits:
        count = source.count(before)
        if count != 1:
            raise RuntimeError(f'Unexpected FFmpeg {label} anchor count: {count}')
    result = source
    for _, before, after in edits:
        result = result.replace(before, after, 1)
    _verify(result, edits)
    return result


def apply_codec_stage_hooks(ffmpeg_source: Path) -> bool:
    """Patch an FFmpeg source root. Return True if either source changed."""
    folder = Path(ffmpeg_source) / 'libavcodec'
    targets = [folder / 'mediacodecdec.c', folder / 'mediacodecdec_common.c']
    originals = {target: target.read_text(encoding='utf-8') for target in targets}
    patched = {target: patch_source(target.name, originals[target]) for target in targets}
    changed = False
    for target in targets:
        if patched[target] != originals[target]:
            target.write_text(patched[target], encoding='utf-8')
            changed = True
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ffmpeg_source', type=Path)
    args = parser.parse_args()
    print('patched' if apply_codec_stage_hooks(args.ffmpeg_source) else 'unchanged')
