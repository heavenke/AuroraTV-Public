"""Fault-inject a read-only locked-source JSON fixture; mutate only temporary copies."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
import hashlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hevc_invalid_atc as patch

FIXTURE: dict[str, str] | None = None


class PatchContracts(unittest.TestCase):
    def sources(self) -> dict[str, str]:
        if FIXTURE is None:
            self.skipTest('Supply --fixture with the read-only source snapshot')
        return dict(FIXTURE)

    def test_complete_patch_is_idempotent_and_only_hevc_is_wired(self) -> None:
        changed = patch.patch_sources(self.sources())
        self.assertEqual(patch.patch_sources(changed), changed)
        self.assertIn('hevc_metadata=remove_invalid_atc=1', changed['libavcodec/mediacodecdec.c'])
        self.assertNotIn('hevc_metadata', changed['libavcodec/mediacodecdec.c'].split('DECLARE_MEDIACODEC_VDEC(h264,')[1].split('\n')[0])
        self.assertIn('{ .i64 = 0 }', changed['libavcodec/bsf/h265_metadata.c'].split('remove_invalid_atc",')[1].split('\n')[1])

    def test_filesystem_second_apply_has_no_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in self.sources().items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding='utf-8')
            self.assertTrue(patch.apply_hevc_invalid_atc(root))
            before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
            self.assertFalse(patch.apply_hevc_invalid_atc(root))
            self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})

    def test_every_missing_duplicate_and_partial_anchor_fails_without_writes(self) -> None:
        tree = ast.parse(Path(patch.__file__).read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'patch_sources')
        assignment = next(n for n in function.body if isinstance(n, ast.Assign) and
                          any(isinstance(t, ast.Name) and t.id == 'edits' for t in n.targets))
        edits = ast.literal_eval(assignment.value)
        count = 0
        for name, replacements in edits.items():
            for before, after in replacements:
                for value in ('', before + before, after):
                    sources = self.sources()
                    sources[name] = sources[name].replace(before, value, 1)
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        for target_name, text in sources.items():
                            target = root / target_name
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_text(text, encoding='utf-8')
                        snapshot = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
                        with self.assertRaises(RuntimeError):
                            patch.apply_hevc_invalid_atc(root)
                        self.assertEqual(snapshot, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in snapshot})
                        self.assertFalse((root / 'libavcodec/bsf/aurora_hevc_invalid_atc.inc').exists())
                    count += 1
        self.assertEqual(count, 39)

    def test_altered_helper_is_rejected_before_source_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in self.sources().items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding='utf-8')
            helper = root / 'libavcodec/bsf/aurora_hevc_invalid_atc.inc'
            helper.write_text('unrecognized helper', encoding='utf-8')
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with self.assertRaises(RuntimeError):
                patch.apply_hevc_invalid_atc(root)
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_only_exact_known_legacy_helper_upgrades_without_other_source_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in self.sources().items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding='utf-8')
            patch.apply_hevc_invalid_atc(root)
            helper = root / 'libavcodec/bsf/aurora_hevc_invalid_atc_filter.inc'
            current = helper.read_text(encoding='utf-8')
            block = '''    // Rewriting encrypted payload would invalidate its original subsample
    // offsets/sizes, even when ciphertext happens to resemble a SEI message.
    if (av_packet_side_data_get(pkt->side_data, pkt->side_data_elems,
                                AV_PKT_DATA_ENCRYPTION_INFO))
        return 0;
'''
            # Reconstruct both shipped revisions to exercise upgrades from native caches.
            v1 = current.replace('static int aurora_hevc_check_hlg(AVBSFContext *bsf, AVPacket *pkt);\n\n', '')
            v1 = v1.replace('    if (err == AVERROR_EOF)\n        ctx->hlg_pps_plus_one = 0;\n', '')
            v1 = v1.replace('AV_PKT_DATA_ENCRYPTION_INFO)) {\n        ctx->hlg_pps_plus_one = 0;\n'
                            '        return 0;\n    }\n    if (aurora_hevc_check_hlg(bsf, pkt))',
                            'AV_PKT_DATA_ENCRYPTION_INFO))')
            self.assertEqual(hashlib.sha256(v1.encode()).hexdigest(), patch.CENC_FILTER_SHA256)
            self.assertEqual(v1.count(block), 1)
            legacy = v1.replace(block, '', 1)
            self.assertEqual(hashlib.sha256(legacy.encode()).hexdigest(), patch.LEGACY_FILTER_SHA256)
            helper.write_text(v1, encoding='utf-8')
            self.assertTrue(patch.apply_hevc_invalid_atc(root))
            self.assertEqual(helper.read_text(encoding='utf-8'), current)
            helper.write_text(legacy, encoding='utf-8')
            others = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file() and p != helper}
            self.assertTrue(patch.apply_hevc_invalid_atc(root))
            self.assertEqual(helper.read_text(encoding='utf-8'), current)
            self.assertEqual(others, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in others})
            self.assertFalse(patch.apply_hevc_invalid_atc(root))
            helper.write_text(legacy + '\n', encoding='utf-8')
            snapshot = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
            with self.assertRaises(RuntimeError):
                patch.apply_hevc_invalid_atc(root)
            self.assertEqual(snapshot, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in snapshot})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', type=Path, required=True)
    arguments, remaining = parser.parse_known_args()
    FIXTURE = json.loads(arguments.fixture.read_text(encoding='utf-8'))
    unittest.main(argv=[sys.argv[0], *remaining])
