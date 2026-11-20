/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Aurora selective invalid HEVC alternative-transfer removal v1.
 * Included by h265_metadata.c after CBS and pixel-description declarations.
 * CBS owns RBSP/EBSP parsing and serialization; never edit escaped bytes here.
 */
static int aurora_hevc_atc_is_defined(unsigned value)
{
    /* H.273 transfer 2 (unspecified) is legal and deliberately preserved. */
    return value <= 255 && value != AVCOL_TRC_RESERVED0 &&
           value != AVCOL_TRC_RESERVED && av_color_transfer_name(value) != NULL;
}

static int aurora_hevc_remove_invalid_atc(CodedBitstreamFragment *au)
{
    int removed = 0;
    for (int i = au->nb_units - 1; i >= 0; i--) {
        CodedBitstreamUnit *unit = &au->units[i];
        if (unit->type != HEVC_NAL_SEI_PREFIX || !unit->content)
            continue;
        H265RawSEI *sei = unit->content;
        SEIRawMessageList *list = &sei->message_list;
        int original_count = list->nb_messages;
        for (int j = list->nb_messages - 1; j >= 0; j--) {
            const SEIRawMessage *message = &list->messages[j];
            if (message->payload_type != SEI_TYPE_ALTERNATIVE_TRANSFER_CHARACTERISTICS ||
                !message->payload)
                continue;
            const SEIRawAlternativeTransferCharacteristics *atc = message->payload;
            if (aurora_hevc_atc_is_defined(atc->preferred_transfer_characteristics))
                continue;
            ff_cbs_sei_delete_message(list, j);
            removed++;
        }
        // Only remove this NAL when deleting invalid messages made it empty.
        // Valid ATC, other SEI payloads, all suffix SEI and all VCL are retained.
        if (original_count && !list->nb_messages)
            ff_cbs_delete_unit(au, i);
    }
    return removed;
}
