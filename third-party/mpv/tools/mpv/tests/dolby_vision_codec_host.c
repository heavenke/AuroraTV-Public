/* Bounded Dolby profile/MIME policy tests, without Android or remote media. */
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#define AVERROR(x) (-(x))
#define AVERROR_INVALIDDATA (-1234)
#define AV_CODEC_ID_HEVC 1
#define AV_PKT_DATA_DOVI_CONF 1
#define AV_LOG_INFO 0
typedef struct {
    uint8_t dv_version_major, dv_version_minor, dv_profile, dv_level;
    uint8_t rpu_present_flag, el_present_flag, bl_present_flag;
    uint8_t dv_bl_signal_compatibility_id, dv_md_compression;
} AVDOVIDecoderConfigurationRecord;
typedef struct { uint8_t *data; size_t size; } AVPacketSideData;
typedef struct { int codec_id; AVPacketSideData *coded_side_data; int nb_coded_side_data; } AVCodecContext;
typedef struct { int aurora_dovi, aurora_dovi_profile; } MediaCodecH264DecContext;
typedef struct { int profile, level; } FFAMediaFormat;
static const AVPacketSideData *av_packet_side_data_get(const AVPacketSideData *p, int n, int type)
{ (void)type; return n > 0 ? p : NULL; }
static void ff_AMediaFormat_setInt32(FFAMediaFormat *f, const char *key, int value)
{ if (!strcmp(key, "profile")) f->profile = value; else if (!strcmp(key, "level")) f->level = value; else abort(); }
#define av_log(...) ((void)0)
#include "../dolby_vision_codec.inc"

int main(void)
{
    AVDOVIDecoderConfigurationRecord cfg = {.dv_profile=5, .dv_level=9,
        .rpu_present_flag=1, .bl_present_flag=1};
    AVPacketSideData side = {(uint8_t *)&cfg, sizeof(cfg)};
    AVCodecContext av = {AV_CODEC_ID_HEVC, &side, 1};
    MediaCodecH264DecContext s = {0};
    FFAMediaFormat f = {0};
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == 0 && f.profile == 0);
    s.aurora_dovi=1;
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == 1 && f.profile == 32 && f.level == 256);
    s.aurora_dovi_profile=8;
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == AVERROR_INVALIDDATA);
    s.aurora_dovi_profile=0;
    side.size=sizeof(cfg)-1;
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == AVERROR_INVALIDDATA);
    side.size=sizeof(cfg);
    cfg.rpu_present_flag=0;
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == AVERROR_INVALIDDATA);
    cfg.rpu_present_flag=1;
    cfg.dv_profile=9;
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == AVERROR(ENOSYS));
    cfg.dv_profile=5;
    cfg.dv_level=32;
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == AVERROR_INVALIDDATA);
    av.nb_coded_side_data=0; f=(FFAMediaFormat){0};
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == 0 && f.profile == 0);
    s.aurora_dovi_profile=5;
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == 1 && f.profile == 32 && f.level == 0);
    s.aurora_dovi_profile=10;
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == AVERROR(ENOSYS));
    av.codec_id=999;
    assert(aurora_mediacodec_dovi_format(&av, &s, &f) == 0);
    return 0;
}
