
/* Aurora optional output observer. LGPL-2.1-or-later, same as this wrapper.
 * These accessors remain inside the combined native component. */
void *aurora_ffmpeg_java_codec(void *opaque);
void *aurora_ffmpeg_ndk_codec(void *opaque);

void *aurora_ffmpeg_java_codec(void *opaque)
{
    FFAMediaCodec *codec = opaque;
    return codec && !strcmp(codec->class->class_name, "amediacodec")
        ? ((FFAMediaCodecJni *)codec)->object : NULL;
}

void *aurora_ffmpeg_ndk_codec(void *opaque)
{
    FFAMediaCodec *codec = opaque;
    return codec && !strcmp(codec->class->class_name, "amediacodec_ndk")
        ? ((FFAMediaCodecNdk *)codec)->impl : NULL;
}
