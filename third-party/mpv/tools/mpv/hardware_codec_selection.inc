/* Aurora hardware selection v2: public capability declarations are hints.
 * Preserve exact-profile preference. A relaxed retry only accepts a decoder
 * positively identified as hardware by the public Android API (API 29+).
 * This changes selection only: stream profile, configure/start failures, and
 * real decoded/rendered-frame checks retain their original meaning.
 * The TLS result is evidence of a fully enumerated missing hardware MIME only;
 * profile/size declarations, failed JNI scans, and unknown legacy candidates
 * must never produce a definite unsupported result.
 */
static _Thread_local int aurora_no_hardware_mime_result;

int aurora_ffmpeg_no_hardware_mime(void);
int aurora_ffmpeg_no_hardware_mime(void)
{
    return aurora_no_hardware_mime_result;
}

char *ff_AMediaCodecList_getCodecNameByType(const char *mime, int profile, int encoder, void *log_ctx)
{
    AuroraHardwareMimeEvidence exact = {0}, relaxed = {0};
    int used_relaxed = 0;
    char *name;

    aurora_no_hardware_mime_result = 0;
    name = aurora_mediacodec_find_hardware(mime, profile, encoder, log_ctx, 0, &exact);

    if (!name && !encoder && profile >= 0 && !av_strncasecmp(mime, "video/", 6)) {
        used_relaxed = 1;
        name = aurora_mediacodec_find_hardware(mime, -1, encoder, log_ctx, 1, &relaxed);
        if (name)
            av_log(log_ctx, AV_LOG_VERBOSE,
                   "Hardware video decoder selected without a declared profile match; "
                   "configuration and decoded output must still succeed.\n");
    }

    if (!name && !encoder && !av_strncasecmp(mime, "video/", 6) &&
        exact.complete && !exact.mime_candidate && !exact.uncertain &&
        (!used_relaxed || (relaxed.complete && !relaxed.mime_candidate && !relaxed.uncertain)))
        aurora_no_hardware_mime_result = 1;

    return name;
}
