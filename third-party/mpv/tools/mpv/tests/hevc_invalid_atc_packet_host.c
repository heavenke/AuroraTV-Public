/* Black-box packet/property fixture, linked to an isolated patched FFmpeg. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libavcodec/bsf.h"
#include "libavcodec/packet.h"
#include "libavcodec/cbs.h"
#include "libavutil/opt.h"
#include "libavutil/mem.h"
#include "libavutil/encryption_info.h"

static int inject_failure, write_calls;
int __real_ff_cbs_write_packet(CodedBitstreamContext *, AVPacket *, CodedBitstreamFragment *);
int __wrap_ff_cbs_write_packet(CodedBitstreamContext *ctx, AVPacket *pkt, CodedBitstreamFragment *fragment)
{
    write_calls++;
    if (inject_failure == 2) {
        // Simulate a writer failing after destructively changing its temporary packet.
        av_buffer_unref(&pkt->buf); pkt->data = NULL; pkt->size = 0; pkt->pts = -999;
        av_packet_free_side_data(pkt);
        return AVERROR_INVALIDDATA;
    }
    return __real_ff_cbs_write_packet(ctx, pkt, fragment);
}

static unsigned char *read_file(const char *path, int *size)
{
    FILE *file = fopen(path, "rb"); assert(file);
    assert(!fseek(file, 0, SEEK_END)); long length = ftell(file);
    assert(length > 0 && length < 64 * 1024 * 1024); rewind(file);
    unsigned char *data = malloc(length); assert(data);
    assert(fread(data, 1, length, file) == (size_t)length); fclose(file);
    *size = length; return data;
}
int main(int argc, char **argv)
{
    assert(argc >= 6 && argc <= 8);
    inject_failure = argc >= 7 ? atoi(argv[6]) : 0;
    int encrypted = argc == 8 ? atoi(argv[7]) : 0;
    int input_size, expected_size, changed = atoi(argv[3]);
    unsigned char *input = read_file(argv[1], &input_size);
    unsigned char *expected = read_file(argv[2], &expected_size);
    AVBSFContext *bsf = NULL;
    assert(av_bsf_alloc(av_bsf_get_by_name("hevc_metadata"), &bsf) >= 0);
    assert(av_opt_set_int(bsf->priv_data, "remove_invalid_atc", 1, 0) >= 0);
    int generic = atoi(argv[4]);
    if (generic) assert(av_opt_set(bsf->priv_data, "aud", "insert", 0) >= 0);
    bsf->par_in->codec_id = AV_CODEC_ID_HEVC;
    bsf->par_in->codec_type = AVMEDIA_TYPE_VIDEO;
    bsf->par_in->width = 3840; bsf->par_in->height = 2160;
    bsf->time_base_in = (AVRational){1, 90000};
    if (atoi(argv[5])) {
        bsf->par_in->extradata = av_mallocz(4 + AV_INPUT_BUFFER_PADDING_SIZE);
        assert(bsf->par_in->extradata);
        memcpy(bsf->par_in->extradata, "\1\2\3\4", 4);
        bsf->par_in->extradata_size = 4;
    }
    int init = av_bsf_init(bsf);
    if (generic && init < 0) {
        puts("upstream generic extradata rejection retained");
        av_bsf_free(&bsf); free(input); free(expected); return 0;
    }
    assert(init >= 0);
    if (atoi(argv[5])) {
        assert(bsf->par_out->extradata_size == 4);
        assert(!memcmp(bsf->par_out->extradata, "\1\2\3\4", 4));
    }
    AVPacket *packet = av_packet_alloc(), *out = av_packet_alloc();
    assert(packet && out && av_new_packet(packet, input_size) >= 0);
    memcpy(packet->data, input, input_size);
    packet->pts = 123456; packet->dts = 120000; packet->duration = 3600;
    packet->pos = 987654; packet->stream_index = 3;
    packet->flags = AV_PKT_FLAG_KEY | AV_PKT_FLAG_DISCARD;
    packet->time_base = (AVRational){1, 90000};
    packet->opaque = (void *)(uintptr_t)0x1234;
    const unsigned char side[] = {7, 0, 0, 1, 0, 0, 3, 9};
    const enum AVPacketSideDataType types[] = {AV_PKT_DATA_STRINGS_METADATA, AV_PKT_DATA_NEW_EXTRADATA};
    for (int i = 0; i < 2; i++) {
        unsigned char *data = av_packet_new_side_data(packet, types[i], sizeof(side)); assert(data);
        memcpy(data, side, sizeof(side));
    }
    if (encrypted) {
        // A real serialized CENC subsample descriptor. Its offsets must never
        // be preserved while the described bytes are shortened or rewritten.
        AVEncryptionInfo *info = av_encryption_info_alloc(1, 16, 16); assert(info);
        info->scheme = 0x63656e63; // cenc, synthetic zero key ID/IV only
        info->subsamples[0].bytes_of_clear_data = 6;
        info->subsamples[0].bytes_of_protected_data = input_size - 6;
        size_t size = 0;
        unsigned char *data = av_encryption_info_add_side_data(info, &size); assert(data);
        av_encryption_info_free(info);
        assert(av_packet_add_side_data(packet, AV_PKT_DATA_ENCRYPTION_INFO, data, size) >= 0);
    }
    AVPacket *original = av_packet_clone(packet); assert(original);
    assert(av_bsf_send_packet(bsf, packet) >= 0);
    if (inject_failure == 1) av_max_alloc(1);
    int result = av_bsf_receive_packet(bsf, out), exit_code = 0;
    av_max_alloc(SIZE_MAX);
    if (inject_failure == 2) assert(write_calls > 0);
    if (generic) {
        assert(result < 0); puts("upstream generic packet rejection retained");
    } else {
        assert(result >= 0);
        if (encrypted && (out->size != expected_size || memcmp(out->data, expected, expected_size))) {
            fputs("encrypted payload was rewritten: subsample descriptor no longer matches\n", stderr);
            exit_code = 2;
            goto cleanup;
        }
        assert(out->size == expected_size && !memcmp(out->data, expected, expected_size));
        assert(out->pts == original->pts && out->dts == original->dts && out->duration == original->duration);
        assert(out->pos == original->pos && out->stream_index == original->stream_index && out->flags == original->flags);
        assert(out->time_base.num == 1 && out->time_base.den == 90000 && out->opaque == original->opaque);
        assert(out->side_data_elems == original->side_data_elems);
        for (int i = 0; i < original->side_data_elems; i++) {
            const AVPacketSideData *reference = &original->side_data[i];
            size_t size = 0; const unsigned char *data = av_packet_get_side_data(out, reference->type, &size);
            assert(size == reference->size && data && !memcmp(data, reference->data, size));
        }
        assert(original->size == input_size && !memcmp(original->data, input, input_size));
        if (!changed) assert(out->buf->data == original->buf->data);
        puts("packet bytes, original ownership, PTS/DTS/duration/flags/side data retained");
    }
cleanup:
    av_packet_free(&original); av_packet_free(&packet); av_packet_free(&out); av_bsf_free(&bsf);
    free(input); free(expected); return exit_code;
}
