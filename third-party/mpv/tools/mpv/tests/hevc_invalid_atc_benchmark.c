/* Optional host-only per-packet cost comparison; no timing acceptance assertion. */
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>
#include "libavformat/avformat.h"
#include "libavcodec/bsf.h"

static int64_t now_ns(void)
{
    struct timespec t; assert(!clock_gettime(CLOCK_MONOTONIC, &t));
    return (int64_t)t.tv_sec * 1000000000 + t.tv_nsec;
}
static int compare(const void *a, const void *b)
{
    int64_t x = *(const int64_t *)a, y = *(const int64_t *)b;
    return (x > y) - (x < y);
}
int main(int argc, char **argv)
{
    assert(argc == 3);
    AVFormatContext *format = NULL;
    assert(avformat_open_input(&format, argv[1], NULL, NULL) >= 0);
    assert(avformat_find_stream_info(format, NULL) >= 0);
    int video = av_find_best_stream(format, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    assert(video >= 0);
    AVBSFContext *filter = NULL;
    const char *chain = atoi(argv[2]) ? "hevc_mp4toannexb,hevc_metadata=remove_invalid_atc=1" : "hevc_mp4toannexb";
    assert(av_bsf_list_parse_str(chain, &filter) >= 0);
    assert(avcodec_parameters_copy(filter->par_in, format->streams[video]->codecpar) >= 0);
    filter->time_base_in = format->streams[video]->time_base;
    assert(av_bsf_init(filter) >= 0);
    AVPacket *packet = av_packet_alloc(), *out = av_packet_alloc(); assert(packet && out);
    int64_t samples[10000], total = 0; int count = 0;
    while (count < 10000 && av_read_frame(format, packet) >= 0) {
        if (packet->stream_index != video) { av_packet_unref(packet); continue; }
        int64_t started = now_ns();
        assert(av_bsf_send_packet(filter, packet) >= 0);
        int result;
        while ((result = av_bsf_receive_packet(filter, out)) >= 0) av_packet_unref(out);
        assert(result == AVERROR(EAGAIN) || result == AVERROR_EOF);
        int64_t elapsed = now_ns() - started;
        samples[count++] = elapsed; total += elapsed;
    }
    assert(count > 0);
    qsort(samples, count, sizeof(*samples), compare);
    printf("{\"packets\":%d,\"totalUs\":%.3f,\"meanUs\":%.3f,\"medianUs\":%.3f,\"p95Us\":%.3f,\"maxUs\":%.3f}\n",
        count, total / 1000.0, total / 1000.0 / count, samples[count / 2] / 1000.0,
        samples[count * 95 / 100] / 1000.0, samples[count - 1] / 1000.0);
    av_packet_free(&packet); av_packet_free(&out); av_bsf_free(&filter); avformat_close_input(&format);
    return 0;
}
