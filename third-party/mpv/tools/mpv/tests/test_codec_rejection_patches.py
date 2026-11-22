"""Fault-inject real FFmpeg fixtures; every filesystem mutation stays in TemporaryDirectory.

Pass --original-wrapper/--original-common and --cached-wrapper/--cached-common.
The cached inputs are read-only snapshots: this test never invokes an apply function on them.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codec_rejection_hooks as rejection
import codec_result_hooks as results

INPUTS: argparse.Namespace | None = None


def rejection_edits() -> tuple[tuple[str, str], ...]:
    """Use the patcher's real anchor inventory for exhaustive corruption injection."""
    source = Path(rejection.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "patch_source")
    assignment = next(node for node in function.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "anchors" for target in node.targets))
    template = Path(rejection.__file__).with_suffix(".inc").read_text(encoding="utf-8").rstrip()
    return eval(compile(ast.Expression(assignment.value), "<anchor inventory>", "eval"), {}, {"template": template})


class PatchContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if INPUTS is None:
            raise unittest.SkipTest("Supply read-only original and cached FFmpeg fixture paths")
        cls.wrapper = Path(INPUTS.original_wrapper).read_text(encoding="utf-8")
        cls.common = Path(INPUTS.original_common).read_text(encoding="utf-8")
        cls.cached_wrapper = Path(INPUTS.cached_wrapper).read_text(encoding="utf-8")
        cls.cached_common = Path(INPUTS.cached_common).read_text(encoding="utf-8")

    def assert_no_write(self, text: str, filename: str, apply) -> None:
        with tempfile.TemporaryDirectory(prefix="aurora-codec-patch-") as directory:
            root = Path(directory)
            target = root / "libavcodec" / filename
            target.parent.mkdir()
            target.write_bytes(text.encode("utf-8"))
            before = target.read_bytes()
            stamp = target.stat().st_mtime_ns
            with self.assertRaises(RuntimeError):
                apply(root)
            self.assertEqual(target.read_bytes(), before, "A rejected partial patch changed source bytes")
            self.assertEqual(target.stat().st_mtime_ns, stamp, "A rejected partial patch rewrote the file")

    def test_original_wrapper_and_current_cache_are_idempotent(self) -> None:
        patched = rejection.patch_source(self.wrapper)
        self.assertEqual(patched.count(rejection.MARKER), 1)
        self.assertEqual(rejection.patch_source(patched), patched)
        self.assertEqual(rejection.patch_source(self.cached_wrapper), self.cached_wrapper)
        self.assertIn("aurora_java_codec_rejection(env, ctx, NULL, 0)", patched)
        self.assertIn("aurora_ndk_codec_rejection(ctx, NULL, 0, status)", patched)

    def test_wrapper_filesystem_second_apply_does_not_rewrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aurora-codec-valid-") as directory:
            root = Path(directory)
            target = root / "libavcodec/mediacodec_wrapper.c"
            target.parent.mkdir()
            target.write_bytes(self.wrapper.encode("utf-8"))
            rejection.apply_codec_rejection_hooks(root)
            before, stamp = target.read_bytes(), target.stat().st_mtime_ns
            rejection.apply_codec_rejection_hooks(root)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(target.stat().st_mtime_ns, stamp)

    def test_each_missing_or_duplicate_wrapper_anchor_fails_without_write(self) -> None:
        for index, (before, _) in enumerate(rejection_edits()):
            self.assertEqual(self.wrapper.count(before), 1)
            for corruption in ("missing", "duplicate"):
                with self.subTest(anchor=index, corruption=corruption):
                    replacement = "/* removed anchor */\n" if corruption == "missing" else before + before
                    bad = self.wrapper.replace(before, replacement, 1)
                    self.assert_no_write(bad, "mediacodec_wrapper.c", rejection.apply_codec_rejection_hooks)

    def test_partial_applied_wrapper_fails_without_write(self) -> None:
        patched = rejection.patch_source(self.wrapper)
        for index, (_, after) in enumerate(rejection_edits()):
            with self.subTest(anchor=index):
                self.assertEqual(patched.count(after), 1)
                bad = patched.replace(after, "/* partial patch */\n", 1)
                self.assert_no_write(bad, "mediacodec_wrapper.c", rejection.apply_codec_rejection_hooks)

    def test_recognized_legacy_declaration_upgrade_is_idempotent(self) -> None:
        patched = rejection.patch_source(self.wrapper)
        legacy = patched.replace("int aurora_ffmpeg_codec_rejection(const FFAMediaCodec *codec);\n", "", 1)
        self.assertEqual(rejection.patch_source(legacy), patched)
        self.assertEqual(rejection.patch_source(rejection.patch_source(legacy)), patched)

    def test_original_result_fixture_and_current_v2_cache_are_idempotent(self) -> None:
        patched = results.patch_source(self.common)
        self.assertIn("Aurora structured video codec lifecycle v2", patched)
        self.assertIn("aurora_mpv_android_codec_result_v2", patched)
        self.assertEqual(results.patch_source(patched), patched)
        self.assertEqual(results.patch_source(self.cached_common), self.cached_common)

    def test_result_missing_and_partial_anchors_fail_without_write(self) -> None:
        patched = results.patch_source(self.common)
        for label, before, after in results._edits():
            with self.subTest(anchor=label, corruption="missing"):
                begin, end = self.common.index(results._START), self.common.index(results._END)
                init = self.common[begin:end]
                self.assertEqual(init.count(before), 1)
                bad = self.common[:begin] + init.replace(before, "/* removed anchor */\n", 1) + self.common[end:]
                self.assert_no_write(bad,
                                     "mediacodecdec_common.c", results.apply_codec_result_hooks)
            with self.subTest(anchor=label, corruption="partial"):
                self.assertEqual(patched.count(after), 1)
                self.assert_no_write(patched.replace(after, "/* partial patch */\n", 1),
                                     "mediacodecdec_common.c", results.apply_codec_result_hooks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("original-wrapper", "original-common", "cached-wrapper", "cached-common"):
        parser.add_argument("--" + field, type=Path, required=True)
    INPUTS = parser.parse_args()
    originals = {name: (path.read_bytes(), path.stat().st_mtime_ns)
                 for name, path in vars(INPUTS).items()}
    outcome = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PatchContracts))
    for name, path in vars(INPUTS).items():
        before, stamp = originals[name]
        if path.read_bytes() != before or path.stat().st_mtime_ns != stamp:
            raise AssertionError("Input fixture changed: " + name)
        print(name + " sha256=" + hashlib.sha256(before).hexdigest())
    sys.exit(0 if outcome.wasSuccessful() else 1)
