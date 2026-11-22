"""Guard the metadata-only HDR extension and refuse stale/ambiguous source layouts."""
from pathlib import Path
import os
import sys
import tempfile
import unittest

RECIPE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RECIPE))
from hdr_metadata import apply_hdr_metadata, ANCHOR, LEGACY_PROPERTIES


PINNED_TRACK_FRAGMENT = '''#include <libavutil/avstring.h>
static int get_track_entry(int item, int action, void *arg, void *ctx)
{
    bool has_crop = mp_rect_w(p.crop) > 0 && mp_rect_h(p.crop) > 0;
    struct m_sub_property props[] = {
        {"demux-w",     SUB_PROP_INT(p.disp_w), .unavailable = !p.disp_w},
        {"demux-h",     SUB_PROP_INT(p.disp_h), .unavailable = !p.disp_h},
        {"dolby-vision-profile", SUB_PROP_INT(p.dv_profile),
                        .unavailable = !p.dovi},
    };
}
'''


class HdrMetadataPatchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / 'player/command.c'
        self.file.parent.mkdir()
        configured = os.environ.get('AURORA_MPV_TEST_SOURCE')
        self.file.write_text((Path(configured) / 'player/command.c').read_text(encoding='utf-8')
                             if configured else PINNED_TRACK_FRAGMENT, encoding='utf-8')

    def test_uses_declared_color_metadata_and_is_idempotent(self):
        self.assertTrue(apply_hdr_metadata(self.root))
        result = self.file.read_bytes()
        self.assertIn(b'struct pl_color_space demux_color = p.color', result)
        self.assertIn(b'pl_transfer_from_av(p.lav_codecpar->color_trc)', result)
        self.assertIn(b'pl_primaries_from_av(p.lav_codecpar->color_primaries)', result)
        self.assertIn(b'"dolby-vision-profile"', result)
        self.assertFalse(apply_hdr_metadata(self.root))
        self.assertEqual(result, self.file.read_bytes())

    def test_unknown_track_layout_is_rejected_without_writing(self):
        self.file.write_text(self.file.read_text().replace('"demux-h"', '"height-renamed"'))
        before = self.file.read_bytes()
        with self.assertRaises(RuntimeError):
            apply_hdr_metadata(self.root)
        self.assertEqual(before, self.file.read_bytes())

    def test_partial_patch_is_rejected_without_writing(self):
        self.file.write_text(self.file.read_text() + '\n/* Aurora demux color metadata */\n')
        before = self.file.read_bytes()
        with self.assertRaises(RuntimeError):
            apply_hdr_metadata(self.root)
        self.assertEqual(before, self.file.read_bytes())

    def test_upgrade_the_initial_readonly_color_property_patch(self):
        self.file.write_text(self.file.read_text().replace(ANCHOR, ANCHOR + LEGACY_PROPERTIES))
        self.assertTrue(apply_hdr_metadata(self.root))
        self.assertFalse(apply_hdr_metadata(self.root))
        self.assertIn('p.lav_codecpar->color_trc', self.file.read_text())


if __name__ == '__main__':
    unittest.main()
