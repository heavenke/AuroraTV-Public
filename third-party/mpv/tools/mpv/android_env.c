/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Android environment entry points kept inside the replaceable LGPL native core.
 */
#include <jni.h>
#include <libavcodec/jni.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>

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
