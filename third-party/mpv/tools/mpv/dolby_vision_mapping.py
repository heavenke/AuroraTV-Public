"""Keep libmpv's established OpenGL renderer, using libplacebo for DV reshaping.

The decoder supplies per-frame AVDOVIMetadata. This patch deliberately does not
invent Dolby metadata from a file name, codec label, or fixed color matrix.
"""
from pathlib import Path


def _replace(text, old, new):
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError('Unexpected mpv Dolby mapping source: ' + old[:60])
    return text.replace(old, new, 1)


def apply_dolby_vision_mapping(mpv: Path):
    video = mpv / 'video/out/gpu/video.c'
    text = video.read_text(encoding='utf-8')
    text = _replace(text, '#include <libavutil/lfg.h>\n',
                    '#include <libavutil/lfg.h>\n#include <libplacebo/shaders/colorspace.h>\n')
    text = _replace(text, '    struct gl_shader_cache *sc;\n',
                    '    struct gl_shader_cache *sc;\n    pl_shader aurora_dovi_shader;\n')
    text = _replace(text, '    mp_image_params_restore_dovi_mapping(&p->image_params);\n',
                    '    // Preserve real per-frame Dolby metadata for the libplacebo bridge.\n'
                    '    if (p->image_params.no_dovi)\n'
                    '        mp_image_params_restore_dovi_mapping(&p->image_params);\n')
    text = _replace(text, '// yuv conversion, and any other conversions before main up/down-scaling\n',
                    '#include "aurora_dolby_vision_mapping.inc"\n\n'
                    '// yuv conversion, and any other conversions before main up/down-scaling\n')
    text = _replace(text, '    // Pre-colormatrix input gamma correction\n',
                    '    if (aurora_pass_dolby_vision(p, &cparams))\n'
                    '        goto color_decoded;\n\n'
                    '    // Pre-colormatrix input gamma correction\n')
    # This code belongs to pass_convert_yuv, and is unique in the locked source.
    text = _replace(text, '    p->components = 3;\n    if (!p->has_alpha) {\n',
                    'color_decoded:\n    p->components = 3;\n    if (!p->has_alpha) {\n')
    text = _replace(text, '    gl_sc_destroy(p->sc);\n',
                    '    gl_sc_destroy(p->sc);\n    pl_shader_free(&p->aurora_dovi_shader);\n')
    video.write_text(text, encoding='utf-8')
    (video.parent / 'aurora_dolby_vision_mapping.inc').write_text(
        Path(__file__).with_suffix('.inc').read_text(encoding='utf-8'), encoding='utf-8')

    # Existing shader-cache uniforms already support vec4 in their underlying RA
    # storage, but the public helper was missing. No array/UBO/driver API changes.
    header = video.parent / 'shader_cache.h'
    text = header.read_text(encoding='utf-8')
    text = _replace(text, 'void gl_sc_uniform_vec3(struct gl_shader_cache *sc, char *name, float f[3]);\n',
                    'void gl_sc_uniform_vec3(struct gl_shader_cache *sc, char *name, float f[3]);\n'
                    'void gl_sc_uniform_vec4(struct gl_shader_cache *sc, char *name, const float f[4]);\n')
    header.write_text(text, encoding='utf-8')
    cache = video.parent / 'shader_cache.c'
    text = cache.read_text(encoding='utf-8')
    text = _replace(text, 'static void transpose2x2(float r[2 * 2])\n',
                    'void gl_sc_uniform_vec4(struct gl_shader_cache *sc, char *name, const float f[4])\n'
                    '{\n'
                    '    struct sc_uniform *u = find_uniform(sc, bstr0(name));\n'
                    '    u->input.type = RA_VARTYPE_FLOAT;\n'
                    '    u->input.dim_v = 4;\n'
                    '    u->glsl_type = "vec4";\n'
                    '    update_uniform_params(sc, u);\n'
                    '    memcpy(u->v.f, f, 4 * sizeof(float));\n'
                    '}\n\n'
                    'static void transpose2x2(float r[2 * 2])\n')
    cache.write_text(text, encoding='utf-8')

    # Upstream's legacy shader-cache did not expose vec4 inputs, so its GL
    # loader never populated the already-declared Uniform4f function pointer.
    # The new dynamic coefficient uniforms require this core GLES 2.0 entry.
    loader = mpv / 'video/out/opengl/common.c'
    text = loader.read_text(encoding='utf-8')
    text = _replace(text, '            DEF_FN(Uniform3f),\n',
                    '            DEF_FN(Uniform3f),\n            DEF_FN(Uniform4f),\n')
    loader.write_text(text, encoding='utf-8')
