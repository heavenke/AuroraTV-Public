/* Regression for the FFmpeg MediaCodec boundary when TS announces HEVC early. */
#include <libavcodec/avcodec.h>
#include <libavutil/error.h>
#include <stdio.h>

int main(void)
{
    const AVCodec *decoder = avcodec_find_decoder_by_name("hevc_mediacodec");
    if (!decoder) return 2;
    AVCodecContext *codec = avcodec_alloc_context3(decoder);
    if (!codec) return 3;

    codec->width = 3840;
    codec->height = 2160;
    AVDictionary *options = NULL;
    av_dict_set(&options, "ndk_codec", "1", 0);
    int result = avcodec_open2(codec, decoder, &options);
    av_dict_free(&options);
    avcodec_free_context(&codec);
    if (result != AVERROR_INVALIDDATA) {
        fprintf(stderr, "Expected AVERROR_INVALIDDATA, got %d\n", result);
        return 1;
    }
    puts("HEVC without codec parameters returned AVERROR_INVALIDDATA without aborting");
    return 0;
}
