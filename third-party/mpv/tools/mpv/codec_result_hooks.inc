/* Aurora structured video codec lifecycle v2.
 * Optional observer only: original return values, codec cleanup, stream profile,
 * and decoding policy are unchanged. Profile is AVCodecContext.profile.
 * Stages: 0 begin, 1 selection/create failed, 2 configure/context failed,
 * 3 start failed, 4 full initialization succeeded after a real codec start.
 * Failure codes retain the selection return or Android configure/start status.
 */
extern void aurora_mpv_android_codec_result(int64_t, int64_t, const char *, const char *,
                                           int, int, int, int, int) __attribute__((weak));
extern void aurora_mpv_android_codec_result_v2(int64_t, int64_t, const char *, const char *,
                                           int, int, int, int, int, int) __attribute__((weak));
extern int aurora_ffmpeg_codec_rejection(const FFAMediaCodec *) __attribute__((weak));

static void aurora_mediacodec_report_result(AVCodecContext *avctx, MediaCodecDecContext *s,
                                           const char *mime, int stage, int code)
{
    if (avctx->codec_type != AVMEDIA_TYPE_VIDEO) return;
    int reason = stage >= 1 && stage <= 3 && aurora_ffmpeg_codec_rejection ?
        aurora_ffmpeg_codec_rejection(stage == 1 ? NULL : s->codec) : 0;
    if (aurora_mpv_android_codec_result_v2)
        aurora_mpv_android_codec_result_v2(s->aurora_client, s->aurora_epoch,
                                       mime ? mime : "", s->codec_name ? s->codec_name : "",
                                       avctx->width, avctx->height, avctx->profile, stage, code, reason);
    else if (aurora_mpv_android_codec_result)
        aurora_mpv_android_codec_result(s->aurora_client, s->aurora_epoch,
                                       mime ? mime : "", s->codec_name ? s->codec_name : "",
                                       avctx->width, avctx->height, avctx->profile, stage, code);
}
