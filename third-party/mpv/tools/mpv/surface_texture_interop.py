#!/usr/bin/env python3
"""Add a second MediaCodec GPU interop before the byte-buffer copy method."""
from pathlib import Path

MARKER = "Aurora MediaCodec texture interop v3"


def apply_surface_texture_interop(source: Path) -> bool:
    recipe = Path(__file__).parent
    driver = source / "video/out/hwdec/hwdec_surfacetexture.c"
    decoder = source / "video/decode/vd_lavc.c"
    changes = {
        "meson.build": [(
            "sources += files('video/out/hwdec/hwdec_aimagereader.c')",
            "sources += files('video/out/hwdec/hwdec_aimagereader.c', 'video/out/hwdec/hwdec_surfacetexture.c')",
        )],
        "video/out/gpu/hwdec.c": [(
            "extern const struct ra_hwdec_driver ra_hwdec_aimagereader;",
            "extern const struct ra_hwdec_driver ra_hwdec_aimagereader;\nextern const struct ra_hwdec_driver ra_hwdec_surfacetexture;",
        ), (
            "    &ra_hwdec_aimagereader,",
            "    &ra_hwdec_aimagereader,\n    &ra_hwdec_surfacetexture,",
        ), (
            "int ra_hwdec_driver_get_imgfmt_for_name(const char *name)",
            """struct ra_hwdec *ra_hwdec_get_by_name(struct ra_hwdec_ctx *ctx, int imgfmt,
                                     const char *name)
{
    for (int n = 0; n < ctx->num_hwdecs; n++) {
        struct ra_hwdec *hw = ctx->hwdecs[n];
        if (strcmp(hw->driver->name, name) == 0 && ra_hwdec_test_format(hw, imgfmt))
            return hw;
    }
    return NULL;
}

int ra_hwdec_driver_get_imgfmt_for_name(const char *name)""",
        )],
        "video/out/gpu/hwdec.h": [(
            "    struct ra_tex *tex[4];",
            "    struct ra_tex *tex[4];\n    bool has_texture_transform;\n    float texture_transform[16];",
        ), (
            "struct ra_hwdec *ra_hwdec_get(struct ra_hwdec_ctx *ctx, int imgfmt);",
            "struct ra_hwdec *ra_hwdec_get(struct ra_hwdec_ctx *ctx, int imgfmt);\nstruct ra_hwdec *ra_hwdec_get_by_name(struct ra_hwdec_ctx *ctx, int imgfmt, const char *name);",
        )],
        "video/out/gpu/video.c": [(
            "    bool flipped;\n};",
            "    bool flipped;\n    bool has_texture_transform;\n    float texture_transform[16];\n};",
        ), (
            "        if (p->image_params.rotate % 180 == 90)\n            MPSWAP(int, img[n].w, img[n].h);",
            """        if (t->has_texture_transform) {
            const float *m = t->texture_transform;
            float tw = t->w, th = t->h;
            struct gl_transform external = {
                {{m[0], -m[4] * tw / th}, {m[1] * th / tw, -m[5]}},
                {(m[12] + m[4]) * tw, (m[13] + m[5]) * th},
            };
            gl_transform_trans(external, &img[n].transform);
        }
        if (p->image_params.rotate % 180 == 90)
            MPSWAP(int, img[n].w, img[n].h);""",
        ), (
            "                    .flipped = p->image_params.vflip,\n                };",
            """                    .flipped = p->image_params.vflip,
                    .has_texture_transform = p->hwdec_mapper->has_texture_transform,
                };
                if (p->hwdec_mapper->has_texture_transform)
                    memcpy(vimg->planes[n].texture_transform, p->hwdec_mapper->texture_transform,
                           sizeof(vimg->planes[n].texture_transform));""",
        ), (
            "        struct ra_tex_upload_params params = {\n            .tex = plane->tex,",
            "        plane->has_texture_transform = false;\n        struct ra_tex_upload_params params = {\n            .tex = plane->tex,",
        ), (
            "    struct ra_hwdec *hwdec = ra_hwdec_get(&p->hwdec_ctx, p->image_params.imgfmt);",
            """    struct ra_hwdec *hwdec = p->image_params.hwdec_surface_texture
        ? ra_hwdec_get_by_name(&p->hwdec_ctx, p->image_params.imgfmt, "android-surface-texture")
        : ra_hwdec_get(&p->hwdec_ctx, p->image_params.imgfmt);""",
        )],
        "video/mp_image.h": [(
            "    enum mp_imgfmt hw_subfmt;   // underlying format for some hwaccel pixfmts",
            "    enum mp_imgfmt hw_subfmt;   // underlying format for some hwaccel pixfmts\n    bool hwdec_surface_texture; // this frame belongs to the matching MediaCodec interop",
        ), (
            "    double pts;\n    /* only after decoder */",
            "    double pts;\n    int64_t hwdec_timestamp_ns; // original codec PTS, before filter-chain timestamp offsets\n    /* only after decoder */",
        )],
        "video/mp_image.c": [(
            "           p1->hw_subfmt == p2->hw_subfmt &&",
            "           p1->hw_subfmt == p2->hw_subfmt &&\n           p1->hwdec_surface_texture == p2->hwdec_surface_texture &&",
        )],
        "video/hwdec.h": [(
            "// For code which still strictly assumes there is 1 (or none) device.",
            """// Restrict a retry to the requested interop while retaining the original format/type checks.
struct mp_hwdec_ctx *hwdec_devices_get_by_driver(struct mp_hwdec_devices *devs,
    int hw_imgfmt, enum AVHWDeviceType device_type, const char *driver_name);

// For code which still strictly assumes there is 1 (or none) device.""",
        )],
        "video/hwdec.c": [(
            "struct mp_hwdec_ctx *hwdec_devices_get_first(struct mp_hwdec_devices *devs)",
            """struct mp_hwdec_ctx *hwdec_devices_get_by_driver(struct mp_hwdec_devices *devs,
    int hw_imgfmt, enum AVHWDeviceType device_type, const char *driver_name)
{
    struct mp_hwdec_ctx *result = NULL;
    mp_mutex_lock(&devs->lock);
    for (int n = 0; n < devs->num_hwctxs; n++) {
        struct mp_hwdec_ctx *device = devs->hwctxs[n];
        AVHWDeviceContext *context = device->av_device_ref
            ? (AVHWDeviceContext *)device->av_device_ref->data : NULL;
        if (device->hw_imgfmt == hw_imgfmt && context && context->type == device_type &&
            device->driver_name && strcmp(device->driver_name, driver_name) == 0) {
            result = device;
            break;
        }
    }
    mp_mutex_unlock(&devs->lock);
    return result;
}

struct mp_hwdec_ctx *hwdec_devices_get_first(struct mp_hwdec_devices *devs)""",
        )],
        "video/decode/vd_lavc.c": [(
            "    bool copying; // if true, outputs sw frames, or copy to sw ourselves",
            "    const char *interop_name; // " + MARKER + "\n    bool copying; // if true, outputs sw frames, or copy to sw ourselves",
        ), (
            '    snprintf(info.name, sizeof(info.name), "%s-%s",\n             info.codec->name, info.method_name);',
            '    snprintf(info.name, sizeof(info.name), "%s-%s%s%s",\n             info.codec->name, info.method_name, info.interop_name ? "-" : "",\n             info.interop_name ? info.interop_name : "");',
        ), (
            "                // Direct variant.\n                add_hwdec_item(infos, num_infos, info);\n\n                // Copy variant.\n                info.copying = true;\n                if (cfg->methods & AV_CODEC_HW_CONFIG_METHOD_HW_DEVICE_CTX)",
            """                // Retain the original method first. A failed codec/output pairing
                // can try a different Surface without changing hardware decode mode.
                add_hwdec_item(infos, num_infos, info);
                if (info.lavc_device == AV_HWDEVICE_TYPE_MEDIACODEC) {
                    struct hwdec_info texture = info;
                    texture.interop_name = "android-surface-texture";
                    add_hwdec_item(infos, num_infos, texture);
                }

                // Copy variant.
                info.copying = true;
                if (cfg->methods & AV_CODEC_HW_CONFIG_METHOD_HW_DEVICE_CTX)""",
        ), (
            "        if (hw_ctx && hw_ctx->av_device_ref)\n            return av_buffer_ref(hw_ctx->av_device_ref);",
            """        if (hwdec->interop_name)
            hw_ctx = hwdec_devices_get_by_driver(ctx->hwdec_devs, imgfmt,
                hwdec->lavc_device, hwdec->interop_name);
        if (hw_ctx && hw_ctx->av_device_ref) {
            if (hw_ctx->driver_name && strcmp(hw_ctx->driver_name, "android-surface-texture") == 0)
                hwdec->interop_name = "android-surface-texture";
            return av_buffer_ref(hw_ctx->av_device_ref);
        }""",
        ), (
            "    if (!ctx->hwdec_notified) {",
            """    res->params.hwdec_surface_texture = ctx->use_hwdec && !ctx->hwdec.copying &&
        ctx->hwdec.interop_name != NULL;

    if (!ctx->hwdec_notified) {""",
        ), (
            "    mpi->pkt_duration = mp_pts_from_av(ctx->pic->duration, &ctx->codec_timebase);",
            """    mpi->pkt_duration = mp_pts_from_av(ctx->pic->duration, &ctx->codec_timebase);
    mpi->hwdec_timestamp_ns = ctx->use_hwdec && ctx->hwdec.interop_name &&
        isfinite(mpi->pts) && mpi->pts > 0 && mpi->pts < 9000000000.0
        ? llrint(mpi->pts * 1000000000.0) : 0;""",
        )],
    }
    if MARKER in decoder.read_text():
        for relative, edits in changes.items():
            content = (source / relative).read_text()
            if any(content.count(new) != 1 for _, new in edits):
                raise RuntimeError("Incomplete MediaCodec interop patch: " + relative)
        content = (recipe / "surface_texture_interop.c").read_bytes()
        changed = not driver.is_file() or driver.read_bytes() != content
        if changed:
            driver.write_bytes(content)
        return changed

    updated = {}
    for relative, edits in changes.items():
        path = source / relative
        content = path.read_text()
        for old, new in edits:
            if content.count(old) != 1:
                raise RuntimeError("Unexpected MediaCodec interop source layout: " + relative)
            content = content.replace(old, new, 1)
        updated[path] = content
    for path, content in updated.items():
        path.write_text(content)
    driver.write_bytes((recipe / "surface_texture_interop.c").read_bytes())
    return True
