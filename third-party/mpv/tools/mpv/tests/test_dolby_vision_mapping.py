import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dolby_vision_mapping import apply_dolby_vision_mapping


class DolbyVisionMappingPatchTest(unittest.TestCase):
    def test_locked_source_markers_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gpu = root / 'video/out/gpu'
            gpu.mkdir(parents=True)
            (gpu / 'video.c').write_text(
                '#include <libavutil/lfg.h>\n'
                '    struct gl_shader_cache *sc;\n'
                '    mp_image_params_restore_dovi_mapping(&p->image_params);\n'
                '// yuv conversion, and any other conversions before main up/down-scaling\n'
                '    // Pre-colormatrix input gamma correction\n'
                '    p->components = 3;\n    if (!p->has_alpha) {\n'
                '    gl_sc_destroy(p->sc);\n')
            (gpu / 'shader_cache.h').write_text(
                'void gl_sc_uniform_vec3(struct gl_shader_cache *sc, char *name, float f[3]);\n')
            (gpu / 'shader_cache.c').write_text('static void transpose2x2(float r[2 * 2])\n')
            loader = root / 'video/out/opengl/common.c'
            loader.parent.mkdir()
            loader.write_text('            DEF_FN(Uniform3f),\n')
            apply_dolby_vision_mapping(root)
            before = {p.name: p.read_bytes() for p in gpu.iterdir()}
            apply_dolby_vision_mapping(root)
            self.assertEqual(before, {p.name: p.read_bytes() for p in gpu.iterdir()})
            video = (gpu / 'video.c').read_text()
            self.assertIn('if (p->image_params.no_dovi)', video)
            self.assertIn('pl_shader_free(&p->aurora_dovi_shader)', video)
            self.assertEqual(1, loader.read_text().count('DEF_FN(Uniform4f)'))

    def test_unknown_source_fails_before_injecting_shader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gpu = root / 'video/out/gpu'
            gpu.mkdir(parents=True)
            (gpu / 'video.c').write_text('upstream layout changed\n')
            with self.assertRaises(RuntimeError):
                apply_dolby_vision_mapping(root)
            self.assertEqual('upstream layout changed\n', (gpu / 'video.c').read_text())
            self.assertFalse((gpu / 'aurora_dolby_vision_mapping.inc').exists())


if __name__ == '__main__':
    unittest.main()
