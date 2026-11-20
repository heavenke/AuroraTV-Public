/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Android environment entry points kept inside the replaceable LGPL native core.
 */
#include <jni.h>
#include <libavcodec/jni.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdint.h>
#include <stdatomic.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <libavutil/error.h>
#include <libavutil/time.h>
#include <media/NdkMediaCodec.h>

__attribute__((visibility("default")))
int aurora_mpv_android_initialize(JavaVM *vm, jobject application_context)
{
    int result = av_jni_set_java_vm(vm, NULL);
    if (result < 0) return result;
    return av_jni_set_android_app_ctx(application_context, NULL);
}

__attribute__((visibility("default")))
const char *aurora_mpv_ffmpeg_license(void) { return avutil_license(); }

__attribute__((visibility("default")))
const char *aurora_mpv_ffmpeg_configuration(void) { return avcodec_configuration(); }

/* Optional output ABI. Only an observer accepting a codec's actual Surface
 * receives callbacks; ordinary libmpv/OpenGL use remains independent of it. */
extern void *aurora_ffmpeg_java_codec(void *);
extern void *aurora_ffmpeg_ndk_codec(void *);
static pthread_mutex_t output_lock = PTHREAD_MUTEX_INITIALIZER;
static _Atomic(jobject) output_observer;
static jmethodID java_codec_created, native_codec_created, native_frame_rendered, native_codec_failed;
static jmethodID prepare_texture_frame, texture_frame_submitted;
static jmethodID codec_result;
static atomic_uint next_codec_token;
static void *media_library;
static media_status_t (*set_frame_callback)(AMediaCodec *, AMediaCodecOnFrameRendered, void *);

/* An explicitly enabled, single-session diagnostic. No JNI or per-frame log IO.
 * Stages: input dequeue, output dequeue, input queue, receive_frame call.
 * Disabled playback only performs the initial atomic identity check. */
typedef struct {
    int64_t calls, inflight, total_us, max_us, ready, again, last_result;
    int64_t start_us, end_us, pts, bytes, tid;
} CodecStage;
static pthread_mutex_t codec_stage_lock = PTHREAD_MUTEX_INITIALIZER;
static atomic_llong codec_stage_client, codec_stage_epoch;
static int64_t codec_stage_start_us;
static CodecStage codec_stages[4];

__attribute__((visibility("default")))
int aurora_mpv_android_codec_stage_control(int64_t client, int64_t epoch, int enabled)
{
    if (client <= 0 || epoch <= 0) return 0;
    int result = 0;
    pthread_mutex_lock(&codec_stage_lock);
    int64_t current = atomic_load(&codec_stage_client);
    int same = current == client && atomic_load(&codec_stage_epoch) == epoch;
    if (enabled && (!current || same)) {
        if (!same) {
            memset(codec_stages, 0, sizeof(codec_stages));
            codec_stage_start_us = av_gettime_relative();
            atomic_store(&codec_stage_epoch, epoch);
            atomic_store(&codec_stage_client, client);
        }
        result = 1;
    } else if (!enabled && same) {
        atomic_store(&codec_stage_client, 0);atomic_store(&codec_stage_epoch, 0);result = 1;
    }
    pthread_mutex_unlock(&codec_stage_lock);
    return result;
}

__attribute__((visibility("default")))
int64_t aurora_mpv_android_codec_stage_begin(int64_t client, int64_t epoch, int stage)
{
    if (stage < 0 || stage >= 4 || atomic_load(&codec_stage_client) != client ||
        atomic_load(&codec_stage_epoch) != epoch || client <= 0) return 0;
    int64_t now = av_gettime_relative(), result = 0;
    pthread_mutex_lock(&codec_stage_lock);
    if (atomic_load(&codec_stage_client) == client && atomic_load(&codec_stage_epoch) == epoch) {
        codec_stages[stage].inflight++;codec_stages[stage].start_us = now;
        codec_stages[stage].tid = gettid();result = now;
    }
    pthread_mutex_unlock(&codec_stage_lock);
    return result;
}

__attribute__((visibility("default")))
void aurora_mpv_android_codec_stage_end(int64_t client, int64_t epoch, int stage,
    int64_t start_us, int result, int64_t pts, int64_t bytes)
{
    if (!start_us || stage < 0 || stage >= 4 || atomic_load(&codec_stage_client) != client ||
        atomic_load(&codec_stage_epoch) != epoch || client <= 0) return;
    int64_t now = av_gettime_relative();
    pthread_mutex_lock(&codec_stage_lock);
    if (atomic_load(&codec_stage_client) == client && atomic_load(&codec_stage_epoch) == epoch &&
        start_us >= codec_stage_start_us) {
        CodecStage *value = &codec_stages[stage];
        int64_t elapsed = now >= start_us ? now - start_us : 0;
        value->calls++;if (value->inflight > 0) value->inflight--;
        value->total_us += elapsed;if (elapsed > value->max_us) value->max_us = elapsed;
        if (result >= 0) value->ready++;
        if (result == (stage < 2 ? -1 : AVERROR(EAGAIN))) value->again++;
        value->last_result = result;value->end_us = now;value->pts = pts;
        if (bytes > 0 && result >= 0) value->bytes += bytes;
    }
    pthread_mutex_unlock(&codec_stage_lock);
}

__attribute__((visibility("default")))
int aurora_mpv_android_codec_stage_snapshot(int64_t client, int64_t epoch, int64_t *out, int count)
{
    if (!out || count < 50) return 0;
    int result = 0;
    pthread_mutex_lock(&codec_stage_lock);
    if (atomic_load(&codec_stage_client) == client && atomic_load(&codec_stage_epoch) == epoch && client > 0) {
        out[0] = av_gettime_relative();out[1] = codec_stage_start_us;
        for (int i = 0; i < 4; i++) {
            CodecStage *v = &codec_stages[i];
            int64_t values[] = {v->calls,v->inflight,v->total_us,v->max_us,v->ready,v->again,
                v->last_result,v->start_us,v->end_us,v->pts,v->bytes,v->tid};
            memcpy(out + 2 + i * 12, values, sizeof(values));
        }
        result = 1;
    }
    pthread_mutex_unlock(&codec_stage_lock);
    return result;
}

static JNIEnv *output_env(int *attached)
{
    JavaVM *vm = av_jni_get_java_vm(NULL);
    JNIEnv *env = NULL;
    *attached = 0;
    if (!vm) return NULL;
    *attached = (*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_6) != JNI_OK;
    if (*attached && (*vm)->AttachCurrentThread(vm, &env, NULL) != JNI_OK) return NULL;
    return env;
}

static void output_env_done(JNIEnv *env, int attached)
{
    if ((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env);
    if (attached) {
        JavaVM *vm = av_jni_get_java_vm(NULL);
        (*vm)->DetachCurrentThread(vm);
    }
}

__attribute__((visibility("default")))
int aurora_mpv_android_set_output_observer(JNIEnv *env, jobject observer)
{
    pthread_mutex_lock(&output_lock);
    if (!atomic_load(&output_observer)) {
        jclass type = (*env)->GetObjectClass(env, observer);
        java_codec_created = (*env)->GetMethodID(env, type, "onCodecCreated",
            "(Landroid/media/MediaCodec;Landroid/view/Surface;JJII)V");
        native_codec_created = (*env)->GetMethodID(env, type, "onNativeCodecCreated",
            "(Landroid/view/Surface;JJII)Z");
        native_frame_rendered = (*env)->GetMethodID(env, type, "onNativeFrameRendered", "(JJJ)V");
        native_codec_failed = (*env)->GetMethodID(env, type, "onNativeCodecFailed", "(J)V");
        prepare_texture_frame = (*env)->GetMethodID(env, type, "prepareTextureFrame", "(Landroid/view/Surface;JJ)J");
        texture_frame_submitted = (*env)->GetMethodID(env, type, "onTextureFrameSubmitted", "(Landroid/view/Surface;JJIJ)V");
        codec_result = (*env)->GetMethodID(env, type, "onCodecResult", "(JJLjava/lang/String;Ljava/lang/String;IIIIII)V");
        (*env)->DeleteLocalRef(env, type);
        if ((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env);
        if (!media_library) media_library = dlopen("libmediandk.so", RTLD_NOW | RTLD_LOCAL);
        if (media_library) set_frame_callback = (void *)dlsym(media_library, "AMediaCodec_setOnFrameRenderedCallback");
        if (java_codec_created && native_codec_created && native_frame_rendered && native_codec_failed &&
            prepare_texture_frame && texture_frame_submitted && codec_result)
            atomic_store(&output_observer, (*env)->NewGlobalRef(env, observer));
    }
    int flags = atomic_load(&output_observer) ? 61 | (set_frame_callback ? 2 : 0) : 0;
    pthread_mutex_unlock(&output_lock);
    return flags;
}

/* Decoder results also cover copy-output codecs, which have no Java Surface.
 * The client nonce and file epoch come from immutable FFmpeg private options;
 * a retired instance can never target the next session reusing its old address. */
__attribute__((visibility("default")))
void aurora_mpv_android_codec_result_v2(int64_t client, int64_t epoch, const char *mime,
    const char *codec, int width, int height, int profile, int stage, int error, int unsupported_reason)
{
    jobject observer = atomic_load(&output_observer);
    if (!observer || client <= 0 || epoch <= 0) return;
    int attached;
    JNIEnv *env = output_env(&attached);
    if (!env) return;
    /* Android codec and MIME identifiers are ASCII. */
    jstring mime_text = (*env)->NewStringUTF(env, mime ? mime : "");
    jstring codec_text = (*env)->NewStringUTF(env, codec ? codec : "");
    if (mime_text && codec_text && !(*env)->ExceptionCheck(env))
        (*env)->CallVoidMethod(env, observer, codec_result, (jlong)client, (jlong)epoch,
            mime_text, codec_text, (jint)width, (jint)height, (jint)profile, (jint)stage, (jint)error,
            (jint)unsupported_reason);
    if (mime_text) (*env)->DeleteLocalRef(env, mime_text);
    if (codec_text) (*env)->DeleteLocalRef(env, codec_text);
    output_env_done(env, attached);
}

__attribute__((visibility("default")))
void aurora_mpv_android_codec_result(int64_t client, int64_t epoch, const char *mime,
    const char *codec, int width, int height, int profile, int stage, int error)
{
    aurora_mpv_android_codec_result_v2(client, epoch, mime, codec, width, height, profile, stage, error, 0);
}

static void ndk_frame(AMediaCodec *codec, void *userdata, int64_t media_time_us, int64_t system_nano)
{
    (void)codec;
    int attached;
    JNIEnv *env = output_env(&attached);
    if (!env) return;
    (*env)->CallVoidMethod(env, atomic_load(&output_observer), native_frame_rendered,
        (jlong)(uintptr_t)userdata, (jlong)media_time_us, (jlong)system_nano);
    output_env_done(env, attached);
}

__attribute__((visibility("default")))
void aurora_mpv_android_codec_started(void *codec, void *surface, int width, int height, int64_t epoch)
{
    jobject observer = atomic_load(&output_observer);
    if (!observer || !surface) return;
    int attached;
    JNIEnv *env = output_env(&attached);
    if (!env) return;
    uint32_t token = atomic_fetch_add(&next_codec_token, 1) + 1;
    if (!token) token = atomic_fetch_add(&next_codec_token, 1) + 1;
    jobject java_codec = aurora_ffmpeg_java_codec(codec);
    if (java_codec) {
        (*env)->CallVoidMethod(env, observer, java_codec_created,
            java_codec, (jobject)surface, (jlong)token, (jlong)epoch, (jint)width, (jint)height);
    } else {
        AMediaCodec *ndk_codec = aurora_ffmpeg_ndk_codec(codec);
        if (ndk_codec) {
            jboolean accepted = (*env)->CallBooleanMethod(env, observer, native_codec_created,
                (jobject)surface, (jlong)token, (jlong)epoch, (jint)width, (jint)height);
            // Texture output verifies its submitted ticket against a real View
            // update and can bind an NDK codec before the API 33 frame callback.
            // Surface output is separately gated on that callback capability.
            if (accepted && set_frame_callback && !(*env)->ExceptionCheck(env) &&
                set_frame_callback(ndk_codec, ndk_frame, (void *)(uintptr_t)token) != AMEDIA_OK)
                (*env)->CallVoidMethod(env, observer, native_codec_failed, (jlong)token);
        }
    }
    output_env_done(env, attached);
}

__attribute__((visibility("default")))
int64_t aurora_mpv_android_prepare_texture_frame(void *surface, int64_t epoch, int64_t pts_us)
{
    jobject observer = atomic_load(&output_observer);
    if (!observer || !surface) return 0;
    int attached;
    JNIEnv *env = output_env(&attached);
    if (!env) return 0;
    jlong stamp = (*env)->CallLongMethod(env, observer, prepare_texture_frame,
        (jobject)surface, (jlong)epoch, (jlong)pts_us);
    if ((*env)->ExceptionCheck(env)) stamp = 0;
    output_env_done(env, attached);
    return stamp;
}

__attribute__((visibility("default")))
void aurora_mpv_android_texture_frame_submitted(void *surface, int64_t epoch, int64_t stamp, int result, int64_t duration_ns)
{
    jobject observer = atomic_load(&output_observer);
    if (!observer || !surface) return;
    int attached;
    JNIEnv *env = output_env(&attached);
    if (!env) return;
    (*env)->CallVoidMethod(env, observer, texture_frame_submitted,
        (jobject)surface, (jlong)epoch, (jlong)stamp, (jint)result, (jlong)duration_ns);
    output_env_done(env, attached);
}
