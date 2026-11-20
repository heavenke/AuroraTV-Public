/* SPDX-License-Identifier: LGPL-2.1-or-later
 * H.265 D.3.38: alternative transfer characteristics persists to the end of
 * the coded layer video sequence. Some MediaCodec decoders forget it after
 * the declaring picture. Restate only a proven BT.2020-compatible HLG signal.
 */
#include "libavcodec/golomb.h"

static void aurora_hevc_hlg_flush(AVBSFContext *bsf)
{
    H265MetadataContext *ctx = bsf->priv_data;
    ctx->hlg_pps_plus_one = 0;
    if (aurora_hevc_sanitize_only(ctx))
        ff_cbs_close(&ctx->common.output);
}

static int aurora_hevc_hlg_picture(H265MetadataContext *ctx,
                                    CodedBitstreamFragment *frag, AVPacket *pkt)
{
    CodedBitstreamH265Context *h265 = ctx->common.output->priv_data;
    H2645Packet *nals = &h265->common.read_packet;
    const H265RawSPS *sps = NULL;
    const H265RawPPS *pps = NULL;
    const H2645NAL *picture = NULL;
    int has_hlg = 0, idr = 0, has_vps = 0;
    unsigned picture_pps;

    // CBS can omit enhancement layers. Only interpret a complete base-layer AU.
    if (frag->nb_units != nals->nb_nals)
        return 0;
    for (int i = 0; i < nals->nb_nals; i++) {
        const H2645NAL *nal = &nals->nals[i];
        const CodedBitstreamUnit *unit = &frag->units[i];
        if (nal->nuh_layer_id || unit->type != nal->type)
            return 0;
        switch (nal->type) {
        case HEVC_NAL_VPS:
            if (picture || has_vps || !unit->content) return 0;
            has_vps = 1;
            break;
        case HEVC_NAL_SPS:
            if (picture || sps || !unit->content) return 0;
            sps = unit->content;
            break;
        case HEVC_NAL_PPS:
            if (picture || pps || !unit->content) return 0;
            pps = unit->content;
            break;
        case HEVC_NAL_SEI_PREFIX: {
            const H265RawSEI *sei = unit->content;
            if (picture || !sei) return 0;
            for (int j = 0; j < sei->message_list.nb_messages; j++) {
                const SEIRawMessage *message = &sei->message_list.messages[j];
                if (message->payload_type == SEI_TYPE_ALTERNATIVE_TRANSFER_CHARACTERISTICS) {
                    const SEIRawAlternativeTransferCharacteristics *atc = message->payload;
                    if (!atc || atc->preferred_transfer_characteristics != AVCOL_TRC_ARIB_STD_B67)
                        return 0;
                    has_hlg = 1;
                }
            }
            break;
        }
        case HEVC_NAL_FD_NUT:
            // Rate-control filler may follow the slice and does not end its sequence.
            break;
        case HEVC_NAL_AUD:
            if (i != 0) return 0;
            break;
        case HEVC_NAL_IDR_W_RADL:
        case HEVC_NAL_IDR_N_LP:
            idr = 1;
            av_fallthrough;
        case HEVC_NAL_TRAIL_N:
        case HEVC_NAL_TRAIL_R: {
            GetBitContext gb = nal->gb;
            if (picture || get_bits_left(&gb) < 3 || !get_bits1(&gb)) return 0;
            if (idr) skip_bits1(&gb);
            picture_pps = get_ue_golomb_long(&gb);
            if (get_bits_left(&gb) < 0 || picture_pps >= HEVC_MAX_PPS_COUNT) return 0;
            picture = nal;
            break;
        }
        default:
            // Other IRAP, EOS, RPU, multilayer or unfamiliar metadata: stop.
            return 0;
        }
    }

    if (!picture) return 0;
    if (idr) {
        return has_hlg && sps && pps &&
               pps->pps_pic_parameter_set_id == picture_pps &&
               pps->pps_seq_parameter_set_id == sps->sps_seq_parameter_set_id &&
               sps->vui_parameters_present_flag && sps->vui.video_signal_type_present_flag &&
               sps->vui.colour_description_present_flag &&
               sps->vui.colour_primaries == AVCOL_PRI_BT2020 &&
               sps->vui.matrix_coefficients == AVCOL_SPC_BT2020_NCL &&
               sps->vui.transfer_characteristics == AVCOL_TRC_BT2020_10
               ? picture_pps + 1 : 0;
    }
    if (has_vps || sps || pps || ctx->hlg_pps_plus_one != picture_pps + 1)
        return 0;
    if (!has_hlg) {
        // Insert one base-layer prefix SEI immediately before the original VCL.
        // All input bytes, including AUD and other SEI, keep their exact order.
        uint8_t prefix[] = { 0, 0, 1, HEVC_NAL_SEI_PREFIX << 1, picture->temporal_id + 1,
                             SEI_TYPE_ALTERNATIVE_TRANSFER_CHARACTERISTICS, 1,
                             AVCOL_TRC_ARIB_STD_B67, 0x80 };
        ptrdiff_t offset = picture->raw_data - frag->data;
        AVPacket *copy;
        if (offset < 3 || offset >= pkt->size || pkt->data[offset - 3] ||
            pkt->data[offset - 2] || pkt->data[offset - 1] != 1 ||
            pkt->size > INT_MAX - (int)sizeof(prefix) - AV_INPUT_BUFFER_PADDING_SIZE)
            return 0;
        offset -= 3;
        if (offset && !pkt->data[offset - 1]) offset--;
        copy = av_packet_alloc();
        if (!copy || av_new_packet(copy, pkt->size + sizeof(prefix)) < 0 ||
            av_packet_copy_props(copy, pkt) < 0) {
            av_packet_free(&copy);
            return 0;
        }
        memcpy(copy->data, pkt->data, offset);
        memcpy(copy->data + offset, prefix, sizeof(prefix));
        memcpy(copy->data + offset + sizeof(prefix), pkt->data + offset, pkt->size - offset);
        av_packet_unref(pkt);
        av_packet_move_ref(pkt, copy);
        av_packet_free(&copy);
    }
    return picture_pps + 1;
}

static int aurora_hevc_check_hlg(AVBSFContext *bsf, AVPacket *pkt)
{
    H265MetadataContext *ctx = bsf->priv_data;
    CodedBitstreamFragment *frag = &ctx->common.fragment;
    static const CodedBitstreamUnitType types[] = {
        HEVC_NAL_VPS, HEVC_NAL_SPS, HEVC_NAL_PPS, HEVC_NAL_SEI_PREFIX
    };
    if (!ctx->hlg_pps_plus_one && !(pkt->flags & AV_PKT_FLAG_KEY))
        return 0;
    if ((pkt->flags & AV_PKT_FLAG_CORRUPT) ||
        av_packet_side_data_get(pkt->side_data, pkt->side_data_elems, AV_PKT_DATA_NEW_EXTRADATA) ||
        av_packet_side_data_get(pkt->side_data, pkt->side_data_elems, AV_PKT_DATA_DOVI_CONF) ||
        av_packet_side_data_get(bsf->par_in->coded_side_data, bsf->par_in->nb_coded_side_data, AV_PKT_DATA_DOVI_CONF)) {
        ctx->hlg_pps_plus_one = 0;
        return 0;
    }
    if (!ctx->common.output) {
        if (ff_cbs_init(&ctx->common.output, AV_CODEC_ID_HEVC, bsf) < 0)
            return 0;
        ctx->common.output->decompose_unit_types = types;
        ctx->common.output->nb_decompose_unit_types = FF_ARRAY_ELEMS(types);
    }
    if (ff_cbs_read_packet(ctx->common.output, frag, pkt) >= 0)
        ctx->hlg_pps_plus_one = aurora_hevc_hlg_picture(ctx, frag, pkt);
    else
        ctx->hlg_pps_plus_one = 0;
    ff_cbs_fragment_reset(frag);
    return ctx->hlg_pps_plus_one != 0;
}
