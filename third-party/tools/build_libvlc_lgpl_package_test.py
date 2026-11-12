import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from build_libvlc_lgpl_package import ABIS, LIBRARIES, package


class NativePackageTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.original = self.root / "original.aar"
        self.output = self.root / "derived.aar"
        self.native = self.root / "native"
        with zipfile.ZipFile(self.original, "w") as source:
            source.writestr("classes.jar", b"unchanged-java-test-fixture")
            source.writestr("AndroidManifest.xml", b"unchanged-manifest-test-fixture")
            source.writestr("res/values/values.xml", b"<resources />")
            source.writestr("jni/x86/libvlc.so", b"old-native-test-fixture")
            source.writestr("assets/lua/playlist/test.lua", b"script-test-fixture")
            source.writestr("assets/hrtfs/test.sofa", b"hrtf-test-fixture")
        for abi, (elf_class, machine) in ABIS.items():
            for library in LIBRARIES:
                path = self.native / abi / library
                path.parent.mkdir(parents=True, exist_ok=True)
                header = bytearray(64)
                header[:4] = b"\x7fELF"
                header[4] = elf_class
                header[5] = 1
                struct.pack_into("<H", header, 18, machine)
                path.write_bytes(header)

    def tearDown(self):
        self.directory.cleanup()

    def test_packaging_preserves_java_and_excludes_old_native_and_assets(self):
        result = package(self.original, self.native, self.output, set())
        with zipfile.ZipFile(self.output) as derived:
            self.assertEqual(derived.read("classes.jar"), b"unchanged-java-test-fixture")
            self.assertEqual(derived.read("AndroidManifest.xml"), b"unchanged-manifest-test-fixture")
            self.assertEqual(len([name for name in derived.namelist() if name.startswith("jni/")]), 6)
            self.assertFalse(any(name.startswith("assets/") for name in derived.namelist()))
            self.assertFalse(any("x86" in name for name in derived.namelist()))
        self.assertEqual(len(result["assets_removed"]), 2)
        self.assertTrue(result["validation"]["java_classes_preserved"])
        saved = json.loads(self.output.with_suffix(".manifest.json").read_text())
        self.assertEqual(saved["classes_jar_sha256"], result["classes_jar_sha256"])

    def test_incorrect_architecture_is_rejected_without_a_partial_output(self):
        path = self.native / "arm64-v8a" / "libvlc.so"
        data = bytearray(path.read_bytes())
        struct.pack_into("<H", data, 18, 62)
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "machine"):
            package(self.original, self.native, self.output, set())
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_suffix(".building").exists())

    def test_original_archive_cannot_be_overwritten(self):
        before = self.original.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            package(self.original, self.native, self.original, set())
        self.assertEqual(self.original.read_bytes(), before)

    def test_truncated_section_table_is_rejected(self):
        for abi, (elf_class, _) in ABIS.items():
            with self.subTest(abi=abi):
                path = self.native / abi / "libvlc.so"
                original = path.read_bytes()
                data = bytearray(original)
                struct.pack_into("<Q" if elf_class == 2 else "<I", data,
                                 40 if elf_class == 2 else 32, len(data) - 1)
                struct.pack_into("<HH", data, 58 if elf_class == 2 else 46, 64, 1)
                path.write_bytes(data)
                try:
                    with self.assertRaisesRegex(ValueError, "Truncated ELF"):
                        package(self.original, self.native, self.output, set())
                    self.assertFalse(self.output.exists())
                finally:
                    path.write_bytes(original)

    def test_asset_retention_requires_explicit_existing_paths(self):
        retained = "assets/lua/playlist/test.lua"
        result = package(self.original, self.native, self.output, {retained})
        self.assertEqual([entry["path"] for entry in result["assets_retained"]], [retained])
        with zipfile.ZipFile(self.output) as derived:
            self.assertIn(retained, derived.namelist())
        with self.assertRaisesRegex(ValueError, "retained asset"):
            package(self.original, self.native, self.output, {"assets/not-present.ttf"})


if __name__ == "__main__":
    unittest.main()
