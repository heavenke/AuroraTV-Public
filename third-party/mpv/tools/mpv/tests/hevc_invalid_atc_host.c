/* Host fixture for the production CBS-list helper; no Android or media source. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { AVCOL_TRC_RESERVED0 = 0, AVCOL_TRC_RESERVED = 3,
       HEVC_NAL_SEI_PREFIX = 39, SEI_TYPE_ALTERNATIVE_TRANSFER_CHARACTERISTICS = 147 };
typedef struct { uint8_t preferred_transfer_characteristics; } SEIRawAlternativeTransferCharacteristics;
typedef struct { unsigned payload_type; void *payload; int identity; } SEIRawMessage;
typedef struct { SEIRawMessage *messages; int nb_messages; } SEIRawMessageList;
typedef struct { SEIRawMessageList message_list; } H265RawSEI;
typedef struct { int type; void *content; int identity; } CodedBitstreamUnit;
typedef struct { CodedBitstreamUnit *units; int nb_units; } CodedBitstreamFragment;
static int message_deletions, unit_deletions;
static const char *av_color_transfer_name(unsigned value)
{
    // The locked FFmpeg names 0/3 "reserved", 2 "unknown", 1..18 otherwise defined.
    return value <= 18 ? "defined-or-reserved" : NULL;
}
static void ff_cbs_sei_delete_message(SEIRawMessageList *list, int at)
{
    assert(at >= 0 && at < list->nb_messages);
    message_deletions++;
    memmove(list->messages + at, list->messages + at + 1,
            (--list->nb_messages - at) * sizeof(*list->messages));
}
static void ff_cbs_delete_unit(CodedBitstreamFragment *fragment, int at)
{
    assert(at >= 0 && at < fragment->nb_units);
    unit_deletions++;
    memmove(fragment->units + at, fragment->units + at + 1,
            (--fragment->nb_units - at) * sizeof(*fragment->units));
}
#include "../hevc_invalid_atc.inc"

int main(void)
{
    int checks = 0;
    for (unsigned transfer = 0; transfer <= 255; transfer++) {
        SEIRawAlternativeTransferCharacteristics atc = { transfer };
        SEIRawMessage messages[] = {{147, &atc, 71}};
        H265RawSEI sei = {{messages, 1}};
        CodedBitstreamUnit units[] = {{39, &sei, 80}};
        CodedBitstreamFragment fragment = {units, 1};
        int valid = transfer != 0 && transfer != 3 && transfer <= 18;
        assert(aurora_hevc_remove_invalid_atc(&fragment) == !valid);
        assert(fragment.nb_units == valid);
        if (valid) assert(messages[0].identity == 71);
        checks += 2 + valid;
    }
    SEIRawAlternativeTransferCharacteristics invalid0 = {0}, invalid3 = {3}, unknown = {255};
    SEIRawAlternativeTransferCharacteristics hlg = {18}, pq = {16}, sdr = {1}, unspecified = {2};
    unsigned char hdr_payload[] = {0, 0, 1, 0, 0, 3, 1};
    SEIRawMessage messages[] = {{137, hdr_payload, 1}, {147, &invalid0, 2}, {147, &hlg, 3},
        {4, hdr_payload, 4}, {147, &invalid3, 5}, {147, &pq, 6}, {147, &sdr, 7},
        {147, &unknown, 8}, {147, &unspecified, 9}, {147, NULL, 10}};
    H265RawSEI mixed = {{messages, 10}};
    SEIRawMessage suffix_message[] = {{147, &invalid0, 11}};
    H265RawSEI suffix = {{suffix_message, 1}}, empty = {{NULL, 0}};
    CodedBitstreamUnit units[] = {{39, &mixed, 21}, {40, &suffix, 22}, {1, NULL, 23}, {39, &empty, 24}};
    CodedBitstreamFragment fragment = {units, 4};
    assert(aurora_hevc_remove_invalid_atc(&fragment) == 3);
    assert(fragment.nb_units == 4 && mixed.message_list.nb_messages == 7);
    int expected[] = {1, 3, 4, 6, 7, 9, 10};
    for (int i = 0; i < 7; i++) assert(messages[i].identity == expected[i]);
    assert(suffix.message_list.nb_messages == 1 && suffix_message[0].identity == 11);
    assert(memcmp(hdr_payload, (unsigned char[]){0, 0, 1, 0, 0, 3, 1}, 7) == 0);
    assert(aurora_hevc_remove_invalid_atc(&fragment) == 0);
    checks += 13;
    printf("invalid ATC CBS helper: %d checks PASS (%d message deletions, %d empty-unit deletions)\n",
           checks, message_deletions, unit_deletions);
    return 0;
}
