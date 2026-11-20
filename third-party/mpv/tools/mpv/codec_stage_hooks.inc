/* AURORA_STAGE_SHARED_BEGIN */
/* Aurora optional codec stage hooks v1. No per-frame JNI or policy changes.
 * Stages: 0 input dequeue, 1 output dequeue, 2 input queue, 3 receive frame.
 * PTS values are microseconds. Queue bytes are attempted bytes: the observer
 * must inspect result before counting them as successfully submitted bytes.
 */
#include "libavutil/mathematics.h"

extern int64_t aurora_mpv_android_codec_stage_begin(int64_t, int64_t, int)
    __attribute__((weak));
extern void aurora_mpv_android_codec_stage_end(int64_t, int64_t, int, int64_t,
                                              int, int64_t, int64_t)
    __attribute__((weak));

static int64_t aurora_codec_stage_start(AVCodecContext *avctx, int64_t client,
                                       int64_t epoch, int stage)
{
    if (avctx->codec_type == AVMEDIA_TYPE_VIDEO &&
        aurora_mpv_android_codec_stage_begin && aurora_mpv_android_codec_stage_end)
        return aurora_mpv_android_codec_stage_begin(client, epoch, stage);
    return 0;
}

static void aurora_codec_stage_finish(int64_t client, int64_t epoch, int stage,
                                      int64_t start_us, int result, int64_t pts_us,
                                      int64_t bytes)
{
    if (start_us > 0 && aurora_mpv_android_codec_stage_end)
        aurora_mpv_android_codec_stage_end(client, epoch, stage, start_us,
                                          result, pts_us, bytes);
}
/* AURORA_STAGE_SHARED_END */

/* AURORA_STAGE_RECEIVE_BEGIN */
/* Aurora receive-frame stage wrapper v1. Preserve every internal return. */
static int64_t aurora_codec_stage_frame_pts_us(AVCodecContext *avctx, const AVFrame *frame)
{
    if (frame->format == AV_PIX_FMT_MEDIACODEC && frame->data[3])
        return ((const MediaCodecBuffer *)frame->data[3])->pts;
    if (frame->pts == AV_NOPTS_VALUE)
        return AV_NOPTS_VALUE;
    if (avctx->pkt_timebase.num && avctx->pkt_timebase.den)
        return av_rescale_q(frame->pts, avctx->pkt_timebase, AV_TIME_BASE_Q);
    return frame->pts;
}

static int mediacodec_receive_frame(AVCodecContext *avctx, AVFrame *frame)
{
    MediaCodecH264DecContext *s = avctx->priv_data;
    const int64_t client = s->aurora_client;
    const int64_t epoch = s->aurora_epoch;
    int64_t start_us = aurora_codec_stage_start(avctx, client, epoch, 3);
    int result = aurora_mediacodec_receive_frame_internal(avctx, frame);

    if (start_us > 0)
        aurora_codec_stage_finish(client, epoch, 3, start_us, result,
                                  result == 0 ? aurora_codec_stage_frame_pts_us(avctx, frame)
                                              : AV_NOPTS_VALUE,
                                  0);
    return result;
}
/* AURORA_STAGE_RECEIVE_END */
