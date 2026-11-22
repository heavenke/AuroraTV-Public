/* Host-only behavioral checks against the production includes. No Android device required.
 * Build with a directory containing the NDK's VM-neutral jni.h, and -pthread.
 */
#define _POSIX_C_SOURCE 200809L
#include <jni.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

typedef struct FFAMediaCodec { int identity; } FFAMediaCodec;
typedef struct FFAMediaFormat {
    const char *mime, *description;
    int32_t width, height;
    int has_mime, has_width, has_height;
} FFAMediaFormat;
/* These are NDK media_status_t values, deliberately different from Java -1010. */
#define AMEDIA_ERROR_UNSUPPORTED (-10002)
#define AMEDIA_ERROR_INVALID_PARAMETER (-10004)
#define av_strncasecmp strncasecmp
static void av_free(void *p) { free(p); }
static void av_freep(void *p) { void *value; memcpy(&value, p, sizeof(value)); free(value); memset(p, 0, sizeof(value)); }
static int ff_AMediaFormat_getString(FFAMediaFormat *f, const char *key, const char **out) {
    if (!f || strcmp(key, "mime") || !f->has_mime) return 0;
    *out = f->mime ? strdup(f->mime) : NULL; return 1;
}
static int ff_AMediaFormat_getInt32(FFAMediaFormat *f, const char *key, int32_t *out) {
    if (!f) return 0;
    if (!strcmp(key, "width") && f->has_width) { *out = f->width; return 1; }
    if (!strcmp(key, "height") && f->has_height) { *out = f->height; return 1; }
    return 0;
}
static char *ff_AMediaFormat_toString(FFAMediaFormat *f) { return f && f->description ? strdup(f->description) : NULL; }

static atomic_uint checks;
#define CHECK(expr) do { atomic_fetch_add(&checks, 1); if (!(expr)) { \
    fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); abort(); } } while (0)
enum { CODEC_EXCEPTION = 1, ILLEGAL_ARGUMENT = 2, OTHER_EXCEPTION = 3 };
typedef struct Throwable { int kind, code; } Throwable;
static char codec_class, argument_class, method_id;
static _Thread_local jthrowable pending;
static _Thread_local jthrowable expected_original;
static _Thread_local int fault;
static _Thread_local unsigned throws, original_deletes;
static Throwable lookup_exception = {OTHER_EXCEPTION, 999};
enum { NO_FAULT, CODEC_CLASS_FAULT, METHOD_FAULT, ERROR_CODE_FAULT, ARGUMENT_CLASS_FAULT };
static jthrowable exception_occurred(JNIEnv *env) { (void)env; return pending; }
static void exception_clear(JNIEnv *env) { (void)env; pending = NULL; }
static jboolean exception_check(JNIEnv *env) { (void)env; return pending != NULL; }
static jclass find_class(JNIEnv *env, const char *name) {
    (void)env;
    if (!strcmp(name, "android/media/MediaCodec$CodecException")) {
        if (fault == CODEC_CLASS_FAULT) { pending = (jthrowable)&lookup_exception; return NULL; }
        return (jclass)&codec_class;
    }
    CHECK(!strcmp(name, "java/lang/IllegalArgumentException"));
    if (fault == ARGUMENT_CLASS_FAULT) { pending = (jthrowable)&lookup_exception; return NULL; }
    return (jclass)&argument_class;
}
static jboolean is_instance_of(JNIEnv *env, jobject object, jclass type) {
    (void)env;
    Throwable *t = (Throwable *)object;
    return type == (jclass)&codec_class ? t->kind == CODEC_EXCEPTION : t->kind == ILLEGAL_ARGUMENT;
}
static jmethodID get_method(JNIEnv *env, jclass type, const char *name, const char *sig) {
    (void)env; CHECK(type == (jclass)&codec_class && !strcmp(name, "getErrorCode") && !strcmp(sig, "()I"));
    if (fault == METHOD_FAULT) { pending = (jthrowable)&lookup_exception; return NULL; }
    return (jmethodID)&method_id;
}
static jint call_int(JNIEnv *env, jobject object, jmethodID method, ...) {
    (void)env; CHECK(method == (jmethodID)&method_id);
    if (fault == ERROR_CODE_FAULT) pending = (jthrowable)&lookup_exception;
    return ((Throwable *)object)->code;
}
static jint throw_original(JNIEnv *env, jthrowable object) {
    (void)env; CHECK(object == expected_original); pending = object; throws++; return 0;
}
static void delete_reference(JNIEnv *env, jobject object) {
    (void)env;
    if (object == expected_original) { CHECK(pending == expected_original); original_deletes++; }
}
static const struct JNINativeInterface methods = {
    .FindClass = find_class, .IsInstanceOf = is_instance_of, .GetMethodID = get_method,
    .CallIntMethod = call_int, .ExceptionOccurred = exception_occurred,
    .ExceptionClear = exception_clear, .ExceptionCheck = exception_check,
    .Throw = throw_original, .DeleteLocalRef = delete_reference,
};
static JNIEnv environment = &methods;

#include "../codec_rejection_hooks.inc"

static FFAMediaCodec codec_a = {1}, codec_b = {2};
static FFAMediaFormat video = {"video/hevc", "mime=video/hevc,width=3840,height=2160", 3840, 2160, 1, 1, 1};
static void java_case(int kind, int code, const FFAMediaFormat *format, int plain, int wanted, int injected_fault) {
    Throwable original = {kind, code}; pending = expected_original = (jthrowable)&original;
    throws = original_deletes = 0; fault = injected_fault;
    aurora_codec_rejection_reset(&codec_a);
    aurora_java_codec_rejection(&environment, &codec_a, format, plain);
    CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == wanted);
    CHECK(pending == (jthrowable)&original && throws == 1 && original_deletes == 1);
    CHECK(original.kind == kind && original.code == code);
    CHECK(aurora_ffmpeg_codec_rejection(&codec_b) == 0);
    pending = expected_original = NULL; fault = NO_FAULT;
}
static void classifications(void) {
    java_case(CODEC_EXCEPTION, -1010, &video, 0, 2, NO_FAULT);
    java_case(CODEC_EXCEPTION, -1010, &video, 1, 2, NO_FAULT);
    int other_codes[] = {1100, 1101, -1100, -1101, -10002, -22, -10004, 0, 123456};
    for (unsigned i = 0; i < sizeof(other_codes)/sizeof(other_codes[0]); i++)
        java_case(CODEC_EXCEPTION, other_codes[i], &video, 1, 0, NO_FAULT);
    java_case(OTHER_EXCEPTION, -1010, &video, 1, 0, NO_FAULT);
    java_case(ILLEGAL_ARGUMENT, 0, &video, 1, 3, NO_FAULT);
    java_case(ILLEGAL_ARGUMENT, 0, &video, 0, 0, NO_FAULT); /* Surface/crypto/encoder/window path */
    java_case(ILLEGAL_ARGUMENT, 0, NULL, 0, 0, NO_FAULT); /* start, not configure */
    FFAMediaFormat bad[] = {
        {"audio/aac", "mime=audio/aac", 3840,2160,1,1,1},
        {NULL, "mime=null",3840,2160,1,1,1},
        {"video/hevc", "width=0",0,2160,1,1,1},
        {"video/hevc", "height=-1",3840,-1,1,1,1},
        {"video/hevc", "no width",3840,2160,1,0,1},
        {"video/hevc", "no height",3840,2160,1,1,0},
        {"video/hevc", "no mime",3840,2160,0,1,1},
        {"video/hevc", "operating-rate=60",3840,2160,1,1,1},
        {"video/hevc", NULL,3840,2160,1,1,1},
    };
    for (unsigned i = 0; i < sizeof(bad)/sizeof(bad[0]); i++)
        java_case(ILLEGAL_ARGUMENT, 0, &bad[i], 1, 0, NO_FAULT);
    java_case(CODEC_EXCEPTION, -1010, &video, 1, 0, CODEC_CLASS_FAULT);
    java_case(CODEC_EXCEPTION, -1010, &video, 1, 0, METHOD_FAULT);
    java_case(CODEC_EXCEPTION, -1010, &video, 1, 0, ERROR_CODE_FAULT);
    java_case(ILLEGAL_ARGUMENT, 0, &video, 1, 0, ARGUMENT_CLASS_FAULT);
    aurora_codec_rejection_reset(&codec_a); pending = NULL;
    aurora_java_codec_rejection(&environment, &codec_a, &video, 1);
    CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == 0 && pending == NULL);

    int statuses[] = {-10002,-1010,-22,-10004,1100,1101,-1100,-1101,-10000,-10005,0,42};
    for (unsigned i = 0; i < sizeof(statuses)/sizeof(statuses[0]); i++) {
        for (int plain = 0; plain <= 1; plain++) {
            int code = statuses[i];
            int wanted = code == -10002 ? 2 : plain && (code == -22 || code == -10004) ? 3 : 0;
            aurora_ndk_codec_rejection(&codec_a, &video, plain, code);
            CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == wanted);
            CHECK(aurora_ffmpeg_codec_rejection(&codec_b) == 0);
        }
    }
    for (unsigned i = 0; i < sizeof(bad)/sizeof(bad[0]); i++) {
        aurora_ndk_codec_rejection(&codec_a, &bad[i], 1, -22);
        CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == 0);
        aurora_ndk_codec_rejection(&codec_a, &bad[i], 1, -10004);
        CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == 0);
    }
}

static void *independent_thread(void *unused) {
    (void)unused;
    CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == 0);
    aurora_ndk_codec_rejection(&codec_b, &video, 1, -22);
    CHECK(aurora_ffmpeg_codec_rejection(&codec_b) == 3);
    CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == 0);
    return NULL;
}
static void ownership(void) {
    aurora_ndk_codec_rejection(&codec_a, &video, 1, -10002);
    CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == 2);
    pthread_t thread; CHECK(pthread_create(&thread, NULL, independent_thread, NULL) == 0);
    CHECK(pthread_join(thread, NULL) == 0);
    CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == 2);
    CHECK(aurora_ffmpeg_codec_rejection(&codec_b) == 0);
    aurora_codec_rejection_reset(&codec_b);
    CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == 0 && aurora_ffmpeg_codec_rejection(&codec_b) == 0);
    aurora_ndk_codec_rejection(&codec_a, &video, 1, -10002);
    aurora_codec_rejection_reset(&codec_a); /* same address, next configure/start */
    CHECK(aurora_ffmpeg_codec_rejection(&codec_a) == 0);
}

enum { AVMEDIA_TYPE_VIDEO = 1, AVMEDIA_TYPE_AUDIO = 2 };
typedef struct AVCodecContext { int codec_type, width, height, profile; } AVCodecContext;
typedef struct MediaCodecDecContext {
    int64_t aurora_client, aurora_epoch;
    const char *codec_name;
    FFAMediaCodec *codec;
} MediaCodecDecContext;
static struct { int calls, stage, code, reason; int64_t client, epoch; } result;
void aurora_mpv_android_codec_result(int64_t client, int64_t epoch, const char *mime, const char *name,
    int width, int height, int profile, int stage, int code) {
    CHECK(!strcmp(mime,"video/hevc") && !strcmp(name,"hardware-test") && width==3840 && height==2160 && profile==2);
    result.calls++; result.stage=stage; result.code=code; result.reason=-1; result.client=client; result.epoch=epoch;
}
#ifndef AURORA_TEST_LEGACY_OBSERVER
void aurora_mpv_android_codec_result_v2(int64_t client, int64_t epoch, const char *mime, const char *name,
    int width, int height, int profile, int stage, int code, int reason) {
    aurora_mpv_android_codec_result(client,epoch,mime,name,width,height,profile,stage,code);
    result.reason=reason;
}
#endif
#include "../codec_result_hooks.inc"
static void result_plumbing(void) {
    AVCodecContext av = {AVMEDIA_TYPE_VIDEO,3840,2160,2};
    MediaCodecDecContext dec = {12345,98765,"hardware-test",&codec_a};
    aurora_ndk_codec_rejection(&codec_a,&video,1,-10002);
    for (int stage=0;stage<=4;stage++) {
        int before=result.calls;
        aurora_mediacodec_report_result(&av,&dec,"video/hevc",stage,-10002);
        CHECK(result.calls==before+1 && result.stage==stage && result.code==-10002);
        CHECK(result.client==12345 && result.epoch==98765);
#ifndef AURORA_TEST_LEGACY_OBSERVER
        CHECK(result.reason==((stage==2 || stage==3)?2:0));
#else
        CHECK(result.reason==-1);
#endif
    }
    av.codec_type=AVMEDIA_TYPE_AUDIO; int before=result.calls;
    aurora_mediacodec_report_result(&av,&dec,"audio/aac",2,-10002);
    CHECK(result.calls==before);
}
int main(void) {
    classifications(); ownership(); result_plumbing();
    printf("PASS codec rejection host checks: %u (%s observer)\n", atomic_load(&checks),
#ifdef AURORA_TEST_LEGACY_OBSERVER
        "legacy"
#else
        "v2"
#endif
    );
    return 0;
}
