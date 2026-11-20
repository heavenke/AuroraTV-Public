#!/usr/bin/env python3
"""Apply the interop change to the pinned upstream tree and verify cache/error handling."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import unittest

RECIPE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RECIPE))
from surface_texture_interop import apply_surface_texture_interop


class SurfaceTexturePatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = os.environ.get("AURORA_MPV_TEST_ARCHIVE")
        if not name:
            raise unittest.SkipTest("Set AURORA_MPV_TEST_ARCHIVE to the pinned mpv archive")
        archive = Path(name)
        locked = json.loads((RECIPE / "sources.lock.json").read_text())["sources"]["mpv"]
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == locked["sha256"]
        cls.temp = tempfile.TemporaryDirectory()
        cls.pristine = Path(cls.temp.name) / "upstream"
        with tarfile.open(archive) as source:
            source.extractall(cls.pristine, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
        cls.pristine = next(p for p in cls.pristine.iterdir() if p.is_dir())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "mpv"
        shutil.copytree(self.pristine, self.source)

    def test_patch_is_idempotent_on_the_pinned_upstream(self):
        self.assertTrue(apply_surface_texture_interop(self.source))
        before = self.snapshot()
        self.assertFalse(apply_surface_texture_interop(self.source))
        self.assertEqual(before, self.snapshot())

    def test_stale_driver_is_refreshed_in_an_already_patched_cache(self):
        apply_surface_texture_interop(self.source)
        driver = self.source / "video/out/hwdec/hwdec_surfacetexture.c"
        driver.write_text("stale cached driver")
        self.assertTrue(apply_surface_texture_interop(self.source))
        self.assertEqual((RECIPE / "surface_texture_interop.c").read_bytes(), driver.read_bytes())

    def test_source_layout_failure_leaves_the_tree_unchanged(self):
        decoder = self.source / "video/decode/vd_lavc.c"
        decoder.write_text(decoder.read_text().replace("    if (!ctx->hwdec_notified) {", "    if (!ctx->hwdec_notified /* changed */) {"))
        before = self.snapshot()
        with self.assertRaises(RuntimeError):
            apply_surface_texture_interop(self.source)
        self.assertEqual(before, self.snapshot())

    def snapshot(self):
        return {p.relative_to(self.source): hashlib.sha256(p.read_bytes()).digest()
                for p in self.source.rglob("*") if p.is_file()}


if __name__ == "__main__":
    unittest.main()
