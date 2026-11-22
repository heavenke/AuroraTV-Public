/* Source-free HEVC Main colour fixtures (32x32 libx265 black IDR).
 * Link to the patched libavcodec and libavutil with -Wl,--wrap=av_new_packet.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "libavcodec/bsf.h"
#include "libavutil/opt.h"

#define NAL "\x00\x00\x01"
#define SETS NAL "\x40\x01\x0c\x01\xff\xff\x01\x60\x00\x00\x03\x00\x90\x00\x00\x03\x00\x00\x03\x00\x1e\x95\x98\x09" \
             NAL "\x42\x01\x01\x01\x60\x00\x00\x03\x00\x90\x00\x00\x03\x00\x00\x03\x00\x1e\xa0\x42\x08\x59\x65\x66\xb9\x32\xbc\x05\xa8\x48\x70\x48\x20\x00\x00\x03\x00\x20\x00\x00\x03\x03\x21" \
             NAL "\x44\x01\xc1\x73\xd0\x89"
#define IDR NAL "\x28\x01\xaf\x1d\x80\xee\x23\x8f\xff\xd8\x99\xe0"
#define HLG NAL "\x4e\x01\x93\x01\x12\x80"
#define PQ  NAL "\x4e\x01\x93\x01\x10\x80"
#define FRAME NAL "\x02\x01\xc0\x80"
#define AUD NAL "\x46\x01\x10"
#define START SETS HLG IDR
#define RPU NAL "\x7c\x01\x81"
#define OTHER_LAYER NAL "\x02\x09\xc0\x80"
#define FILLER NAL "\x4c\x01\xff\xff\x80"
#define EOS NAL "\x48\x01\x80"
#define PASS(in, flags) packet(ctx, in, sizeof(in)-1, in, sizeof(in)-1, flags, -1)
#define REPEAT() packet(ctx, AUD FRAME, sizeof(AUD FRAME)-1, AUD HLG FRAME, sizeof(AUD HLG FRAME)-1, 0, -1)
#define SIDE(type) packet(ctx, FRAME, sizeof(FRAME)-1, FRAME, sizeof(FRAME)-1, 0, type)

static int fail_size;
int __real_av_new_packet(AVPacket *, int);
int __wrap_av_new_packet(AVPacket *pkt, int size)
{
    return fail_size && size == fail_size ? AVERROR(ENOMEM) : __real_av_new_packet(pkt, size);
}

static void packet(AVBSFContext *ctx, const char *input, int size, const char *expected,
                   int expected_size, int flags, int side)
{
    AVPacket *pkt = av_packet_alloc(), *out = av_packet_alloc();
    assert(pkt && out && av_new_packet(pkt, size) == 0);
    memcpy(pkt->data, input, size);
    pkt->pts = 90000; pkt->dts = 86400; pkt->duration = 3600; pkt->flags = flags;
    pkt->pos = 98765; pkt->stream_index = 1; pkt->opaque = ctx;
    uint8_t *tag = av_packet_new_side_data(pkt, AV_PKT_DATA_STRINGS_METADATA, 4);
    assert(tag); memcpy(tag, "tag", 4);
    if (side >= 0) assert(av_packet_new_side_data(pkt, side, 16));
    AVPacket *original = av_packet_clone(pkt); assert(original);
    assert(av_bsf_send_packet(ctx, pkt) == 0 && av_bsf_receive_packet(ctx, out) == 0);
    static int sequence; sequence++;
    if (out->size != expected_size) fprintf(stderr, "packet %d expected %d bytes, received %d\n", sequence, expected_size, out->size);
    assert(out->size == expected_size && !memcmp(out->data, expected, expected_size));
    assert(original->size == size && !memcmp(original->data, input, size));
    assert(out->pts == original->pts && out->dts == original->dts && out->duration == original->duration);
    assert(out->flags == flags && out->pos == original->pos && out->opaque == ctx && out->stream_index == 1);
    assert(out->side_data_elems == original->side_data_elems &&
           !memcmp(av_packet_get_side_data(out, AV_PKT_DATA_STRINGS_METADATA, NULL), "tag", 4));
    if (size == expected_size) assert(out->data == original->data);
    av_packet_free(&original); av_packet_free(&out); av_packet_free(&pkt);
}

int main(void)
{
    AVBSFContext *ctx = NULL;
    assert(av_bsf_alloc(av_bsf_get_by_name("hevc_metadata"), &ctx) == 0);
    ctx->par_in->codec_id = AV_CODEC_ID_HEVC; ctx->par_in->codec_type = AVMEDIA_TYPE_VIDEO;
    assert(av_opt_set_int(ctx->priv_data, "remove_invalid_atc", 1, 0) == 0 && av_bsf_init(ctx) == 0);
    PASS(START, AV_PKT_FLAG_KEY); REPEAT(); PASS(HLG FRAME, 0); REPEAT();
    packet(ctx, FRAME FILLER, sizeof(FRAME FILLER)-1,
           HLG FRAME FILLER, sizeof(HLG FRAME FILLER)-1, 0, -1);
    REPEAT();
    PASS(SETS IDR, AV_PKT_FLAG_KEY); PASS(FRAME, 0);
    PASS(SETS PQ IDR, AV_PKT_FLAG_KEY); PASS(FRAME, 0);
    PASS(START, AV_PKT_FLAG_KEY); PASS(PQ FRAME, 0); PASS(FRAME, 0);
    PASS(START, AV_PKT_FLAG_KEY); PASS(RPU FRAME, 0); PASS(FRAME, 0);
    PASS(START, AV_PKT_FLAG_KEY); PASS(OTHER_LAYER FRAME, 0); PASS(FRAME, 0);
    PASS(START, AV_PKT_FLAG_KEY); PASS(EOS, 0); PASS(FRAME, 0);
    PASS(START, AV_PKT_FLAG_KEY); av_bsf_flush(ctx); PASS(FRAME, 0);
    PASS(START, AV_PKT_FLAG_KEY); SIDE(AV_PKT_DATA_ENCRYPTION_INFO); PASS(FRAME, 0);
    PASS(START, AV_PKT_FLAG_KEY); SIDE(AV_PKT_DATA_NEW_EXTRADATA); PASS(FRAME, 0);
    PASS(START, AV_PKT_FLAG_KEY); SIDE(AV_PKT_DATA_DOVI_CONF); PASS(FRAME, 0);
    PASS(START, AV_PKT_FLAG_KEY); PASS(FRAME, AV_PKT_FLAG_CORRUPT); PASS(FRAME, 0);
    PASS(START, AV_PKT_FLAG_KEY); fail_size = sizeof(HLG FRAME)-1; PASS(FRAME, 0);
    fail_size = 0; PASS(FRAME, 0);
    av_bsf_free(&ctx);
    puts("HLG repetition, HDR transitions, EOS/flush, RPU, layer, CENC and allocation rollback passed");
    return 0;
}
