/* SPDX-License-Identifier: LGPL-2.1-or-later
 * MediaCodec/SurfaceTexture interop for outputs rejected by AImageReader.
 * The GL consumer remains on mpv's render thread, including buffer acquisition.
 */
#include <jni.h>
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>
#include <libavcodec/mediacodec.h>
#include <libavutil/hwcontext.h>
#include <libavutil/hwcontext_mediacodec.h>
#include "misc/jni.h"
#include "video/out/gpu/hwdec.h"
#include "video/out/opengl/ra_gl.h"

struct texture_owner {
    struct mp_hwdec_ctx hwctx;
    jobject surface;
    jobject texture;
    jfloatArray matrix_array;
    jmethodID update_image;
    jmethodID get_timestamp;
    jmethodID get_matrix;
    jmethodID release_texture;
    jmethodID release_surface;
    GLuint texture_id;
    bool registered;
    bool mapped;
};

struct texture_mapper {
    int64_t last_timestamp;
    bool owns_texture;
};

static bool clear_exception(JNIEnv *env)
{
    if (!(*env)->ExceptionCheck(env))
        return false;
    (*env)->ExceptionClear(env);
    return true;
}

static int64_t monotonic_ns(void)
{
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (int64_t)now.tv_sec * 1000000000LL + now.tv_nsec;
}

static jmethodID method(JNIEnv *env, jclass type, const char *name, const char *signature)
{
    jmethodID id = (*env)->GetMethodID(env, type, name, signature);
    return clear_exception(env) ? NULL : id;
}

static void uninit(struct ra_hwdec *hw)
{
    struct texture_owner *owner = hw->priv;
    if (owner->registered)
        hwdec_devices_remove(hw->devs, &owner->hwctx);
    av_buffer_unref(&owner->hwctx.av_device_ref);
    JNIEnv *env = MP_JNI_GET_ENV(hw);
    if (env) {
        if (owner->surface) {
            (*env)->CallVoidMethod(env, owner->surface, owner->release_surface);
            clear_exception(env);
            (*env)->DeleteGlobalRef(env, owner->surface);
        }
        if (owner->texture) {
            (*env)->CallVoidMethod(env, owner->texture, owner->release_texture);
            clear_exception(env);
            (*env)->DeleteGlobalRef(env, owner->texture);
        }
        if (owner->matrix_array)
            (*env)->DeleteGlobalRef(env, owner->matrix_array);
    }
    if (owner->texture_id) {
        GL *gl = ra_gl_get(hw->ra_ctx->ra);
        gl->DeleteTextures(1, &owner->texture_id);
    }
}

static int init(struct ra_hwdec *hw)
{
    struct texture_owner *owner = hw->priv;
    if (!ra_is_gl(hw->ra_ctx->ra))
        return -1;
    JNIEnv *env = MP_JNI_GET_ENV(hw);
    if (!env)
        return -1;
    GL *gl = ra_gl_get(hw->ra_ctx->ra);
    static const char *es2_extensions[] = {"GL_OES_EGL_image_external", NULL};
    static const char *es3_extensions[] = {"GL_OES_EGL_image_external_essl3", NULL};
    if (!gl_check_extension(gl->extensions, es2_extensions[0]) &&
        !gl_check_extension(gl->extensions, es3_extensions[0]))
        return -1;
    hw->glsl_extensions = gl_check_extension(gl->extensions, es3_extensions[0])
        ? es3_extensions : es2_extensions;

    gl->GenTextures(1, &owner->texture_id);
    gl->BindTexture(GL_TEXTURE_EXTERNAL_OES, owner->texture_id);
    gl->TexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    gl->TexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    gl->TexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    gl->TexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    if ((*env)->PushLocalFrame(env, 8) < 0) {
        clear_exception(env);
        return -1;
    }
    int result = -1;
    jclass texture_class = (*env)->FindClass(env, "android/graphics/SurfaceTexture");
    if (clear_exception(env) || !texture_class)
        goto done;
    jclass surface_class = (*env)->FindClass(env, "android/view/Surface");
    if (clear_exception(env) || !surface_class)
        goto done;
    jmethodID texture_constructor = method(env, texture_class, "<init>", "(I)V");
    jmethodID surface_constructor = method(env, surface_class, "<init>", "(Landroid/graphics/SurfaceTexture;)V");
    owner->update_image = method(env, texture_class, "updateTexImage", "()V");
    owner->get_timestamp = method(env, texture_class, "getTimestamp", "()J");
    owner->get_matrix = method(env, texture_class, "getTransformMatrix", "([F)V");
    owner->release_texture = method(env, texture_class, "release", "()V");
    owner->release_surface = method(env, surface_class, "release", "()V");
    if (!texture_constructor || !surface_constructor ||
        !owner->update_image || !owner->get_timestamp || !owner->get_matrix ||
        !owner->release_texture || !owner->release_surface)
        goto done;
    jobject texture = (*env)->NewObject(env, texture_class, texture_constructor, (jint)owner->texture_id);
    if (clear_exception(env) || !texture)
        goto done;
    owner->texture = (*env)->NewGlobalRef(env, texture);
    if (clear_exception(env) || !owner->texture)
        goto done;
    jobject surface = (*env)->NewObject(env, surface_class, surface_constructor, texture);
    if (clear_exception(env) || !surface)
        goto done;
    owner->surface = (*env)->NewGlobalRef(env, surface);
    if (clear_exception(env) || !owner->surface)
        goto done;
    jfloatArray matrix = (*env)->NewFloatArray(env, 16);
    if (clear_exception(env) || !matrix)
        goto done;
    owner->matrix_array = (*env)->NewGlobalRef(env, matrix);
    if (clear_exception(env) || !owner->texture || !owner->surface || !owner->matrix_array)
        goto done;

    AVBufferRef *device = av_hwdevice_ctx_alloc(AV_HWDEVICE_TYPE_MEDIACODEC);
    if (!device)
        goto done;
    AVHWDeviceContext *context = (void *)device->data;
    AVMediaCodecDeviceContext *codec = context->hwctx;
    codec->surface = owner->surface;
    if (av_hwdevice_ctx_init(device) < 0) {
        av_buffer_unref(&device);
        goto done;
    }
    owner->hwctx = (struct mp_hwdec_ctx) {
        .driver_name = hw->driver->name,
        .av_device_ref = device,
        .hw_imgfmt = IMGFMT_MEDIACODEC,
    };
    hwdec_devices_add(hw->devs, &owner->hwctx);
    owner->registered = true;
    result = 0;
done:
    (*env)->PopLocalFrame(env, NULL);
    return result;
}

static int mapper_init(struct ra_hwdec_mapper *mapper)
{
    struct texture_owner *owner = mapper->owner->priv;
    struct texture_mapper *state = mapper->priv;
    if (owner->mapped)
        return -1;
    const struct ra_format *format = ra_find_unorm_format(mapper->ra, 1, 4);
    if (!format || format->ctype != RA_CTYPE_UNORM)
        return -1;
    mapper->dst_params = mapper->src_params;
    mapper->dst_params.imgfmt = IMGFMT_RGB0;
    mapper->dst_params.hw_subfmt = 0;
    struct ra_tex_params params = {
        .dimensions = 2, .w = mapper->src_params.w, .h = mapper->src_params.h, .d = 1,
        .format = format, .render_src = true, .src_linear = true, .external_oes = true,
    };
    mapper->tex[0] = ra_create_wrapped_tex(mapper->ra, &params, owner->texture_id);
    if (!mapper->tex[0])
        return -1;
    JNIEnv *env = MP_JNI_GET_ENV(mapper);
    if (!env)
        return -1;
    // Discard a retained image from a preceding decoder before this mapper
    // releases its first buffer. A format change cannot inherit that image.
    (*env)->CallVoidMethod(env, owner->texture, owner->update_image);
    if (clear_exception(env))
        return -1;
    state->last_timestamp = (*env)->CallLongMethod(env, owner->texture, owner->get_timestamp);
    if (clear_exception(env))
        return -1;
    owner->mapped = true;
    state->owns_texture = true;
    return 0;
}

static void mapper_uninit(struct ra_hwdec_mapper *mapper)
{
    struct texture_owner *owner = mapper->owner->priv;
    struct texture_mapper *state = mapper->priv;
    ra_tex_free(mapper->ra, &mapper->tex[0]);
    mapper->has_texture_transform = false;
    if (state->owns_texture)
        owner->mapped = false;
}

static int mapper_map(struct ra_hwdec_mapper *mapper)
{
    struct texture_owner *owner = mapper->owner->priv;
    struct texture_mapper *state = mapper->priv;
    JNIEnv *env = MP_JNI_GET_ENV(mapper);
    if (!env || mapper->src->imgfmt != IMGFMT_MEDIACODEC)
        return -1;
    AVMediaCodecBuffer *buffer = (void *)mapper->src->planes[3];
    if (!buffer || av_mediacodec_release_buffer(buffer, 1) < 0)
        return -1;

    // updateTexImage may return before the producer queues this buffer. A repeated
    // timestamp is the preceding image and must never count as a newly mapped frame.
    int64_t deadline = monotonic_ns() + 250000000LL;
    int64_t expected = mapper->src->hwdec_timestamp_ns;
    int64_t timestamp;
    do {
        (*env)->CallVoidMethod(env, owner->texture, owner->update_image);
        if (clear_exception(env))
            return -1;
        timestamp = (*env)->CallLongMethod(env, owner->texture, owner->get_timestamp);
        if (clear_exception(env))
            return -1;
        if (timestamp > 0 && timestamp != state->last_timestamp &&
            (expected <= 0 || llabs(timestamp - expected) <= 1000))
            break;
        struct timespec delay = {.tv_nsec = 1000000};
        nanosleep(&delay, NULL);
    } while (monotonic_ns() < deadline);
    if (timestamp <= 0 || timestamp == state->last_timestamp ||
        (expected > 0 && llabs(timestamp - expected) > 1000)) {
        MP_WARN(mapper, "No fresh MediaCodec texture within the acquisition budget\n");
        return -1;
    }
    (*env)->CallVoidMethod(env, owner->texture, owner->get_matrix, owner->matrix_array);
    if (clear_exception(env))
        return -1;
    (*env)->GetFloatArrayRegion(env, owner->matrix_array, 0, 16, mapper->texture_transform);
    if (clear_exception(env))
        return -1;
    for (int i = 0; i < 16; i++) {
        if (!isfinite(mapper->texture_transform[i]))
            return -1;
    }
    state->last_timestamp = timestamp;
    mapper->has_texture_transform = true;
    return 0;
}

const struct ra_hwdec_driver ra_hwdec_surfacetexture = {
    .name = "android-surface-texture",
    .priv_size = sizeof(struct texture_owner),
    .imgfmts = {IMGFMT_MEDIACODEC, 0},
    .device_type = AV_HWDEVICE_TYPE_MEDIACODEC,
    .init = init,
    .uninit = uninit,
    .mapper = &(const struct ra_hwdec_mapper_driver) {
        .priv_size = sizeof(struct texture_mapper),
        .init = mapper_init,
        .uninit = mapper_uninit,
        .map = mapper_map,
    },
};
