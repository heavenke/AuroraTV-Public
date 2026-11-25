#!/usr/bin/env python3
"""Return a real rendering error when vo_gpu marked the completed draw as broken."""
from pathlib import Path

MARKER = "Aurora GPU render failure result v1"


def apply_gpu_render_failure(source: Path) -> bool:
    edits = {
        "video/out/gpu/video.h": (
            "void gl_video_reset(struct gl_video *p);",
            "// " + MARKER + ": internal last-draw status, not a public libmpv ABI.\n"
            "bool gl_video_frame_broken(const struct gl_video *p);\n"
            "void gl_video_reset(struct gl_video *p);",
        ),
        "video/out/gpu/video.c": (
            "void gl_video_reset(struct gl_video *p)\n{",
            "// " + MARKER + "\n"
            "bool gl_video_frame_broken(const struct gl_video *p)\n"
            "{\n"
            "    return p->broken_frame;\n"
            "}\n\n"
            "void gl_video_reset(struct gl_video *p)\n{",
        ),
        "video/out/gpu/libmpv_gpu.c": (
            "    gl_video_render_frame(p->renderer, frame, &target, RENDER_FRAME_DEF);\n"
            "    p->context->fns->done_frame(p->context, frame->display_synced);\n\n"
            "    return 0;",
            "    gl_video_render_frame(p->renderer, frame, &target, RENDER_FRAME_DEF);\n"
            "    // " + MARKER + ": retain normal backend cleanup even for a rejected draw.\n"
            "    bool broken = gl_video_frame_broken(p->renderer);\n"
            "    p->context->fns->done_frame(p->context, frame->display_synced);\n\n"
            "    return broken ? MPV_ERROR_GENERIC : 0;",
        ),
    }
    current = {relative: (source / relative).read_text(encoding="utf-8") for relative in edits}
    if any(MARKER in text for text in current.values()):
        if any(current[relative].count(new) != 1 for relative, (_, new) in edits.items()):
            raise RuntimeError("Incomplete GPU rendering-error patch")
        return False
    changed = {}
    for relative, (old, new) in edits.items():
        if current[relative].count(old) != 1:
            raise RuntimeError("Unexpected GPU rendering-error source layout: " + relative)
        changed[relative] = current[relative].replace(old, new, 1)
    for relative, text in changed.items():
        (source / relative).write_text(text, encoding="utf-8")
    return True
