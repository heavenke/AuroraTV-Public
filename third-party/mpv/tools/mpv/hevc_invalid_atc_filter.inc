/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Transactional, fail-open wrapper for remove_invalid_atc-only mode.
 * Other hevc_metadata operations retain the upstream generic BSF semantics.
 */
static int aurora_hevc_sanitize_only(const H265MetadataContext *ctx)
{
    return ctx->remove_invalid_atc && ctx->aud == BSF_ELEMENT_PASS &&
           !ctx->sample_aspect_ratio.num && ctx->video_format == -1 &&
           ctx->video_full_range_flag == -1 && ctx->colour_primaries == -1 &&
           ctx->transfer_characteristics == -1 && ctx->matrix_coefficients == -1 &&
           ctx->chroma_sample_loc_type == -1 && !ctx->tick_rate.num &&
           !ctx->poc_proportional_to_timing_flag && ctx->num_ticks_poc_diff_one == -1 &&
           ctx->crop_left == -1 && ctx->crop_right == -1 && ctx->crop_top == -1 &&
           ctx->crop_bottom == -1 && ctx->width == -1 && ctx->height == -1 &&
           ctx->level == LEVEL_UNSET;
}

static int aurora_hevc_sanitize_init(AVBSFContext *bsf)
{
    H265MetadataContext *ctx = bsf->priv_data;
    static const CodedBitstreamUnitType parsed_types[] = { HEVC_NAL_SEI_PREFIX };
    int err = ff_cbs_init(&ctx->common.input, AV_CODEC_ID_HEVC, bsf);
    if (err < 0) {
        ff_cbs_close(&ctx->common.input);
        return 0; // An optional metadata correction must not prevent decoding.
    }
    // ATC, mastering display, content light and opaque/user payloads do not need
    // slice/parameter-set reconstruction. Unsupported context-dependent SEI is
    // left intact on read failure. Complex SPS/VCL remain opaque original data.
    ctx->common.input->decompose_unit_types = parsed_types;
    ctx->common.input->nb_decompose_unit_types = FF_ARRAY_ELEMS(parsed_types);
    return 0;
}

static int aurora_hevc_check_hlg(AVBSFContext *bsf, AVPacket *pkt);

static int aurora_hevc_metadata_filter(AVBSFContext *bsf, AVPacket *pkt)
{
    H265MetadataContext *ctx = bsf->priv_data;
    CodedBitstreamFragment *frag = &ctx->common.fragment;
    AVPacket *rewritten = NULL;
    int err;
    if (!aurora_hevc_sanitize_only(ctx))
        return ff_cbs_bsf_generic_filter(bsf, pkt);

    err = ff_bsf_get_packet_ref(bsf, pkt);
    if (err == AVERROR_EOF)
        ctx->hlg_pps_plus_one = 0;
    if (err < 0)
        return err; // Preserve the original input/EAGAIN/EOF contract.
    // Rewriting encrypted payload would invalidate its original subsample
    // offsets/sizes, even when ciphertext happens to resemble a SEI message.
    if (av_packet_side_data_get(pkt->side_data, pkt->side_data_elems,
                                AV_PKT_DATA_ENCRYPTION_INFO)) {
        ctx->hlg_pps_plus_one = 0;
        return 0;
    }
    if (aurora_hevc_check_hlg(bsf, pkt))
        return 0;
    if (!ctx->common.input)
        return 0;
    if (ff_cbs_read_packet(ctx->common.input, frag, pkt) < 0)
        goto unchanged;
    if (!aurora_hevc_remove_invalid_atc(frag))
        goto unchanged;
    // Do not manufacture an empty packet (MediaCodec interprets it as EOS) or
    // discard packet-side metadata when no other units can safely be retained.
    if (!frag->nb_units)
        goto unchanged;

    rewritten = av_packet_alloc();
    if (!rewritten || av_packet_ref(rewritten, pkt) < 0)
        goto unchanged;
    // This changes only the temporary packet's payload. PTS/DTS/duration,
    // flags and all side data stay copied from the original. Never expose a
    // partial CBS write or its failure to the hardware decode path.
    if (ff_cbs_write_packet(ctx->common.input, rewritten, frag) < 0)
        goto unchanged;
    av_packet_unref(pkt);
    av_packet_move_ref(pkt, rewritten);
unchanged:
    av_packet_free(&rewritten);
    ff_cbs_fragment_reset(frag);
    return 0;
}
