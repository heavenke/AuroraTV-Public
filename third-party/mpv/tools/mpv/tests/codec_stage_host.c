/* Host fixture template: test_codec_stage_hooks.py inserts the production
 * _observed_call replacements and includes the unmodified production .inc.
 */
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stdint.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define AVMEDIA_TYPE_VIDEO 0
#define AVMEDIA_TYPE_AUDIO 1
#define AV_PIX_FMT_MEDIACODEC 88
#define AV_NOPTS_VALUE INT64_MIN
typedef struct AVRational { int num, den; } AVRational;
#define AV_TIME_BASE_Q ((AVRational){1,1000000})
typedef struct MediaCodecBuffer { int64_t pts; } MediaCodecBuffer;
typedef struct AVFrame { int format; unsigned char *data[8]; int64_t pts; } AVFrame;
typedef struct AVCodecContext { int codec_type; AVRational pkt_timebase; void *priv_data; } AVCodecContext;
typedef struct FakeCodec { int identity; } FakeCodec;
typedef struct MediaCodecDecContext { FakeCodec *codec; int64_t aurora_client, aurora_epoch; } MediaCodecDecContext;
typedef struct MediaCodecH264DecContext { MediaCodecDecContext *ctx; int64_t aurora_client, aurora_epoch; } MediaCodecH264DecContext;
typedef struct BufferInfo { int64_t presentationTimeUs; int size; } BufferInfo;

static atomic_uint checks;
#define CHECK(expr) do { atomic_fetch_add(&checks,1); if (!(expr)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#expr); abort(); } } while (0)
static FakeCodec codec = {77};
static MediaCodecDecContext common = {&codec,202,404};
static MediaCodecH264DecContext decoder = {&common,501,902};
static AVCodecContext context = {AVMEDIA_TYPE_VIDEO,{1,90000},&decoder};
static int api_result, api_calls, receive_calls, begin_calls, end_calls, start_enabled = 1;
static int wanted_stage;
static int64_t wanted_client, wanted_epoch, end_pts, end_bytes;
static int end_result;
static int mutate_owner;
static pthread_mutex_t gate = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition = PTHREAD_COND_INITIALIZER;
static int block_api, entered_api, release_api;

static int api_call(void) {
    api_calls++;
    if (mutate_owner) { common.aurora_client=999;common.aurora_epoch=998;decoder.aurora_client=997;decoder.aurora_epoch=996; }
    pthread_mutex_lock(&gate);
    if (block_api) {
        entered_api=1;pthread_cond_broadcast(&condition);
        while (!release_api) pthread_cond_wait(&condition,&gate);
    }
    pthread_mutex_unlock(&gate);
    return api_result;
}
static int ff_AMediaCodec_dequeueInputBuffer(FakeCodec *c, int64_t timeout) {
    CHECK(c==&codec && (timeout==0 || timeout==10000));return api_call();
}
static int ff_AMediaCodec_dequeueOutputBuffer(FakeCodec *c, BufferInfo *info, int64_t timeout) {
    CHECK(c==&codec && timeout==5000);
    int result=api_call();
    if (result>=0) { info->presentationTimeUs=1234567; info->size=4096; }
    return result;
}
static int ff_AMediaCodec_queueInputBuffer(FakeCodec *c, int index, int offset, size_t size, int64_t pts, int flags) {
    CHECK(c==&codec && index==7 && offset==0 && pts==7654321);
    CHECK((size==188 && flags==0) || (size==0 && flags==4));return api_call();
}
static int aurora_mediacodec_receive_frame_internal(AVCodecContext *avctx, AVFrame *frame) {
    CHECK(avctx==&context && frame!=NULL);receive_calls++;return api_call();
}
#ifndef AURORA_TEST_NO_BEGIN
int64_t aurora_mpv_android_codec_stage_begin(int64_t client,int64_t epoch,int stage) {
    CHECK(client==wanted_client && epoch==wanted_epoch && stage==wanted_stage);begin_calls++;
    return start_enabled > 0 ? 1000+stage : start_enabled < 0 ? -7 : 0;
}
#endif
#ifndef AURORA_TEST_NO_END
void aurora_mpv_android_codec_stage_end(int64_t client,int64_t epoch,int stage,int64_t start,int result,int64_t pts,int64_t bytes) {
    CHECK(client==wanted_client && epoch==wanted_epoch && stage==wanted_stage && start==1000+stage);
    end_calls++;end_result=result;end_pts=pts;end_bytes=bytes;
}
#endif

/* AURORA_INCLUDE */

static int outer_dequeue(void) {
    AVCodecContext *avctx=&context; MediaCodecH264DecContext *s=&decoder; int index;
    /* AURORA_OUTER_DEQUEUE */
    return index;
}
static int inner_dequeue(void) {
    AVCodecContext *avctx=&context; MediaCodecDecContext *s=&common; FakeCodec *codec=s->codec;
    int64_t input_dequeue_timeout_us=10000; int index;
    /* AURORA_INNER_DEQUEUE */
    return index;
}
static int output_dequeue(void) {
    AVCodecContext *avctx=&context; MediaCodecDecContext *s=&common; FakeCodec *codec=s->codec;
    int64_t output_dequeue_timeout_us=5000; BufferInfo info; int index;
    /* AURORA_OUTPUT_DEQUEUE */
    return index;
}
static int queue_eos(void) {
    AVCodecContext *avctx=&context; MediaCodecDecContext *s=&common; FakeCodec *codec=s->codec;
    int index=7,flags=4,status;int64_t pts=7654321;
    /* AURORA_QUEUE_EOS */
    return status;
}
static int queue_data(void) {
    AVCodecContext *avctx=&context; MediaCodecDecContext *s=&common; FakeCodec *codec=s->codec;
    int index=7,status;size_t size=188;int64_t pts=7654321;
    /* AURORA_QUEUE_DATA */
    return status;
}
static int observer_present(void) {
#if defined(AURORA_TEST_NO_BEGIN) || defined(AURORA_TEST_NO_END)
    return 0;
#else
    return 1;
#endif
}
static void reset_case(int stage,int outer) {
    common.aurora_client=202;common.aurora_epoch=404;decoder.aurora_client=501;decoder.aurora_epoch=902;
    wanted_client=outer?501:202;wanted_epoch=outer?902:404;wanted_stage=stage;
    api_calls=receive_calls=begin_calls=end_calls=0;end_result=999;end_pts=end_bytes=999;
    context.codec_type=AVMEDIA_TYPE_VIDEO;start_enabled=1;mutate_owner=block_api=entered_api=release_api=0;
}
static void check_calls(int observed,int result,int64_t pts,int64_t bytes) {
    CHECK(api_calls==1);
    CHECK(begin_calls==observed && end_calls==observed);
    if (observed) CHECK(end_result==result && end_pts==pts && end_bytes==bytes);
}
static void api_cases(void) {
    int (*functions[])(void)={outer_dequeue,inner_dequeue,output_dequeue,queue_eos,queue_data};
    int stages[]={0,0,1,2,2};int results[]={0,7,-11,-541478725,-22};
    for (unsigned f=0;f<5;f++) for (unsigned r=0;r<5;r++) {
        reset_case(stages[f],f==0);api_result=results[r];
        CHECK(functions[f]()==api_result);
        int64_t pts=f==2?(api_result>=0?1234567:AV_NOPTS_VALUE):f>=3?7654321:AV_NOPTS_VALUE;
        int64_t bytes=f==2?(api_result>=0?4096:0):f==4?188:0;
        check_calls(observer_present(),api_result,pts,bytes);
    }
    for (unsigned f=0;f<5;f++) {
        reset_case(stages[f],f==0);api_result=-11;context.codec_type=AVMEDIA_TYPE_AUDIO;
        CHECK(functions[f]()==-11);check_calls(0,-11,0,0);
        reset_case(stages[f],f==0);api_result=-22;start_enabled=0;
        CHECK(functions[f]()==-22 && api_calls==1 && end_calls==0);
        CHECK(begin_calls==observer_present());
        reset_case(stages[f],f==0);api_result=-22;start_enabled=-1;
        CHECK(functions[f]()==-22 && api_calls==1 && end_calls==0);
        CHECK(begin_calls==observer_present());
        reset_case(stages[f],f==0);api_result=0;mutate_owner=1;
        CHECK(functions[f]()==0);CHECK(begin_calls==observer_present() && end_calls==observer_present());
    }
}
static void receive_cases(void) {
    MediaCodecBuffer buffer={333333};
    AVFrame frame={AV_PIX_FMT_MEDIACODEC,{0},999};frame.data[3]=(unsigned char *)&buffer;
    int codes[]={0,-11,-541478725,-22,123};
    for (unsigned i=0;i<5;i++) {
        reset_case(3,1);api_result=codes[i];AVFrame before=frame;
        CHECK(mediacodec_receive_frame(&context,&frame)==api_result && receive_calls==1);
        CHECK(before.format==frame.format && before.pts==frame.pts && !memcmp(before.data,frame.data,sizeof(frame.data)));
        check_calls(observer_present(),api_result,api_result==0?333333:AV_NOPTS_VALUE,0);
    }
    reset_case(3,1);api_result=0;frame.format=1;frame.pts=90000;
    CHECK(mediacodec_receive_frame(&context,&frame)==0);check_calls(observer_present(),0,1000000,0);
    reset_case(3,1);api_result=0;frame.pts=AV_NOPTS_VALUE;
    CHECK(mediacodec_receive_frame(&context,&frame)==0);check_calls(observer_present(),0,AV_NOPTS_VALUE,0);
    reset_case(3,1);api_result=0;frame.pts=1234;context.pkt_timebase=(AVRational){0,0};
    CHECK(mediacodec_receive_frame(&context,&frame)==0);check_calls(observer_present(),0,1234,0);
    context.pkt_timebase=(AVRational){1,90000};
    reset_case(3,1);api_result=-11;frame.format=AV_PIX_FMT_MEDIACODEC;frame.data[3]=(unsigned char *)(uintptr_t)1;
    CHECK(mediacodec_receive_frame(&context,&frame)==-11);check_calls(observer_present(),-11,AV_NOPTS_VALUE,0);
    reset_case(3,1);api_result=0;context.codec_type=AVMEDIA_TYPE_AUDIO;
    CHECK(mediacodec_receive_frame(&context,&frame)==0);check_calls(0,0,0,0);
    reset_case(3,1);api_result=0;start_enabled=0;
    CHECK(mediacodec_receive_frame(&context,&frame)==0 && api_calls==1 && end_calls==0);
    CHECK(begin_calls==observer_present());
    reset_case(3,1);api_result=0;start_enabled=-1;
    CHECK(mediacodec_receive_frame(&context,&frame)==0 && api_calls==1 && end_calls==0);
    CHECK(begin_calls==observer_present());
    reset_case(3,1);api_result=0;mutate_owner=1;frame.data[3]=(unsigned char *)&buffer;
    CHECK(mediacodec_receive_frame(&context,&frame)==0);check_calls(observer_present(),0,333333,0);
    if (!observer_present()) {
        reset_case(3,1);api_result=0;
        CHECK(mediacodec_receive_frame(&context,&frame)==0);check_calls(0,0,0,0);
    }
}
static int blocked_result;
static int (*blocked_function)(void);
static int blocked_receive(void) {
    AVFrame frame={AV_PIX_FMT_MEDIACODEC,{0},AV_NOPTS_VALUE};
    return mediacodec_receive_frame(&context,&frame);
}
static void *blocked_queue(void *unused) { (void)unused;blocked_result=blocked_function();return NULL; }
static void blocking_case(void) {
    int (*functions[])(void)={outer_dequeue,inner_dequeue,output_dequeue,queue_eos,queue_data,blocked_receive};
    int stages[]={0,0,1,2,2,3};
    for (unsigned f=0;f<6;f++) {
        reset_case(stages[f],f==0 || f==5);api_result=-22;block_api=1;blocked_function=functions[f];pthread_t thread;
        CHECK(pthread_create(&thread,NULL,blocked_queue,NULL)==0);
        pthread_mutex_lock(&gate);
        while (!entered_api) pthread_cond_wait(&condition,&gate);
        CHECK(api_calls==1 && begin_calls==observer_present() && end_calls==0);
        release_api=1;pthread_cond_broadcast(&condition);pthread_mutex_unlock(&gate);
        CHECK(pthread_join(thread,NULL)==0);
        CHECK(blocked_result==-22);
        check_calls(observer_present(),-22,(f==3 || f==4)?7654321:AV_NOPTS_VALUE,f==4?188:0);
    }
}
int main(void) { api_cases();receive_cases();blocking_case();printf("PASS stage host: %u assertions, observer=%d\n",atomic_load(&checks),observer_present());return 0; }
