/* Aurora opt-in Dolby Vision MediaCodec v1.
 * Dolby rendering is deliberately caller-owned: only a native HDR-capable
 * Surface may request this path. Never infer Dolby Vision from HEVC/10-bit.
 * RPU-only streams need an explicit profile obtained by the caller's bounded
 * demux inspection, not a guessed profile or a second network connection.
 */
static int aurora_mediacodec_dovi_format(AVCodecContext *avctx,
                                         MediaCodecH264DecContext *s,
                                         FFAMediaFormat *format)
{
    const AVPacketSideData *side;
    const AVDOVIDecoderConfigurationRecord *cfg = NULL;
    int profile = s->aurora_dovi_profile;
    int level = 0;

    if (!s->aurora_dovi || avctx->codec_id != AV_CODEC_ID_HEVC)
        return 0;

    side = av_packet_side_data_get(avctx->coded_side_data,
                                  avctx->nb_coded_side_data,
                                  AV_PKT_DATA_DOVI_CONF);
    if (side) {
        if (!side->data || side->size < sizeof(*cfg))
            return AVERROR_INVALIDDATA;
        cfg = (const AVDOVIDecoderConfigurationRecord *)side->data;
        if (!cfg->bl_present_flag || !cfg->rpu_present_flag ||
            (profile && profile != cfg->dv_profile))
            return AVERROR_INVALIDDATA;
        profile = cfg->dv_profile;
        level = cfg->dv_level;
    }

    if (!profile)
        return 0;
    /* HEVC-based Android Dolby profiles only. Profile 9 is AVC, 10 is AV1. */
    if (profile != 4 && profile != 5 && profile != 7 && profile != 8)
        return AVERROR(ENOSYS);
    /* Preserve future positive level declarations without an undefined shift. */
    if (level > 31)
        return AVERROR_INVALIDDATA;

    ff_AMediaFormat_setInt32(format, "profile", 1 << profile);
    if (level > 0)
        ff_AMediaFormat_setInt32(format, "level", 1 << (level - 1));
    av_log(avctx, AV_LOG_INFO,
           "Dolby Vision hardware requested: profile=%d level=%d\n", profile, level);
    return 1;
}
