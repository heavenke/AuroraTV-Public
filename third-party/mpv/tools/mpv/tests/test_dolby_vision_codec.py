"""Exercise the opt-in policy and patch against pinned/cached FFmpeg sources."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

RECIPE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RECIPE))
from dolby_vision_codec import apply_dolby_vision_codec
from hardware_codec_selection import apply_hardware_codec_selection


class DolbyPolicyTest(unittest.TestCase):
    def test_profile_policy(self):
        cc = shutil.which(os.environ.get('CC', 'cc'))
        if not cc:
            self.skipTest('Host C compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'dovi-policy'
            subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(RECIPE / 'tests/dolby_vision_codec_host.c'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


class DolbyPatchTest(unittest.TestCase):
    def setUp(self):
        configured = os.environ.get('AURORA_FFMPEG_TEST_SOURCE')
        if not configured:
            self.skipTest('Set AURORA_FFMPEG_TEST_SOURCE to the pinned FFmpeg source')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'libavcodec').mkdir()
        for name in ('mediacodecdec.c', 'mediacodecdec_common.c', 'mediacodec_wrapper.c', 'mediacodec_wrapper.h'):
            shutil.copyfile(Path(configured) / 'libavcodec' / name, self.root / 'libavcodec' / name)
        apply_hardware_codec_selection(self.root)

    def snapshot(self):
        return {p.name: p.read_bytes() for p in (self.root / 'libavcodec').iterdir()}

    def test_idempotent_and_composes_with_hardware_selector(self):
        self.assertTrue(apply_dolby_vision_codec(self.root))
        before = self.snapshot()
        self.assertFalse(apply_dolby_vision_codec(self.root))
        self.assertFalse(apply_hardware_codec_selection(self.root))
        self.assertEqual(before, self.snapshot())

    def test_partial_or_unknown_source_does_not_write_any_file(self):
        wrapper = self.root / 'libavcodec/mediacodec_wrapper.c'
        wrapper.write_text(wrapper.read_text().replace('static FFAMediaFormat *mediaformat_jni_newFromObject(void *object)',
                                                      'static FFAMediaFormat *unknown_layout(void)'))
        before = self.snapshot()
        with self.assertRaises(RuntimeError):
            apply_dolby_vision_codec(self.root)
        self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
