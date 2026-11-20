/* Aurora codec rejection observations v1.
 * Observe exceptions/status without changing them or the original return path.
 * This TLS record is only read immediately by the same decoder-init thread.
 */
#include <string.h>
static _Thread_local const FFAMediaCodec *aurora_rejection_owner;
static _Thread_local int aurora_rejection_reason;
extern int aurora_ffmpeg_no_hardware_mime(void) __attribute__((weak));
int aurora_ffmpeg_codec_rejection(const FFAMediaCodec *codec);

static void aurora_codec_rejection_reset(const FFAMediaCodec *codec)
{
    aurora_rejection_owner = codec;
    aurora_rejection_reason = 0;
}

int aurora_ffmpeg_codec_rejection(const FFAMediaCodec *codec)
{
    if (!codec)
        return aurora_ffmpeg_no_hardware_mime && aurora_ffmpeg_no_hardware_mime() ? 1 : 0;
    return codec == aurora_rejection_owner ? aurora_rejection_reason : 0;
}

static int aurora_plain_video_format(const FFAMediaFormat *source)
{
    FFAMediaFormat *format = (FFAMediaFormat *)source;
    int32_t width = 0, height = 0;
    const char *mime = NULL;
    int valid = ff_AMediaFormat_getString(format, "mime", &mime) && mime &&
        !av_strncasecmp(mime, "video/", 6) &&
        ff_AMediaFormat_getInt32(format, "width", &width) && width > 0 &&
        ff_AMediaFormat_getInt32(format, "height", &height) && height > 0;
    av_freep(&mime);
    /* A rejected performance override does not prove the video is unsupported. */
    char *description = valid ? ff_AMediaFormat_toString(format) : NULL;
    valid = valid && description && !strstr(description, "operating-rate");
    av_free(description);
    return valid;
}

static void aurora_java_codec_rejection(JNIEnv *env, const FFAMediaCodec *codec,
    const FFAMediaFormat *format, int plain_video_configuration)
{
    jthrowable original = (*env)->ExceptionOccurred(env);
    if (!original) return;
    (*env)->ExceptionClear(env);
    int reason = 0;
    jclass codec_error = (*env)->FindClass(env, "android/media/MediaCodec$CodecException");
    if ((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env);
    if (codec_error && (*env)->IsInstanceOf(env, original, codec_error)) {
        jmethodID error_code = (*env)->GetMethodID(env, codec_error, "getErrorCode", "()I");
        if (error_code && !(*env)->ExceptionCheck(env)) {
            jint code = (*env)->CallIntMethod(env, original, error_code);
            /* Framework media ERROR_UNSUPPORTED, not the NDK translated enum. */
            if (!(*env)->ExceptionCheck(env) && code == -1010) reason = 2;
        }
    } else if (plain_video_configuration) {
        jclass argument_error = (*env)->FindClass(env, "java/lang/IllegalArgumentException");
        if (!(*env)->ExceptionCheck(env) && argument_error &&
            (*env)->IsInstanceOf(env, original, argument_error) && aurora_plain_video_format(format)) reason = 3;
        if (argument_error) (*env)->DeleteLocalRef(env, argument_error);
    }
    if ((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env);
    if (codec_error) (*env)->DeleteLocalRef(env, codec_error);
    aurora_rejection_owner = codec;
    aurora_rejection_reason = reason;
    /* Preserve the very same throwable for FFmpeg's existing exception handler. */
    (*env)->Throw(env, original);
    (*env)->DeleteLocalRef(env, original);
}

static void aurora_ndk_codec_rejection(const FFAMediaCodec *codec,
    const FFAMediaFormat *format, int plain_video_configuration, int status)
{
    aurora_rejection_owner = codec;
    aurora_rejection_reason = status == AMEDIA_ERROR_UNSUPPORTED ? 2 :
        (status == -22 || status == AMEDIA_ERROR_INVALID_PARAMETER) &&
            plain_video_configuration && aurora_plain_video_format(format) ? 3 : 0;
}
