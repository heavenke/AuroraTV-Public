from pathlib import Path

root = Path("/root/.cache/aurora-vlc-lgpl/source")
script = root / "buildsystem/build-libvlc.sh"
text = script.read_text()
anchor = "VLC_MODULE_BLACKLIST=\"\n"
addition = """VLC_MODULE_BLACKLIST="
    dummy
    rc
    file_logger
    syslog
    lua
    stream_out_(cycle|rtp)
    hqdn3d
    rotate
    deinterlace(_.*)?
"""
if addition not in text:
    if text.count(anchor) != 1:
        raise RuntimeError("Pinned Android module blacklist block changed")
    script.write_text(text.replace(anchor, addition, 1))
