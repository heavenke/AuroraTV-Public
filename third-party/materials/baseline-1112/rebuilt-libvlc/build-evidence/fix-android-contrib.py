from pathlib import Path

root = Path("/root/.cache/aurora-vlc-lgpl/source/vlc")
rules = root / "contrib/src/zvbi/rules.mak"
text = rules.read_text()
anchor = "ifdef HAVE_ANDROID\n# discard bogus pthread_cancel calls\n"
replacement = "ifdef HAVE_ANDROID\n# Android has no Linux V4L capture or pthread cancellation API.\nZVBICONF += --disable-v4l\n# discard bogus pthread_cancel calls\n"
if replacement not in text:
    if anchor not in text:
        raise RuntimeError("The pinned zvbi Android configuration block changed")
    rules.write_text(text.replace(anchor, replacement, 1))
