"""Apply the documented Android-only compatibility and plugin-selection patches."""

import argparse
import hashlib
import json
from pathlib import Path


MODULE_EXCLUSIONS = """    dummy
    rc
    file_logger
    syslog
    lua
    stream_out_(cycle|rtp)
    hqdn3d
    rotate
    deinterlace(_.*)?
"""


def prepare(source):
    script = source / "buildsystem/build-libvlc.sh"
    text = script.read_text()
    anchor = 'VLC_MODULE_BLACKLIST="\n'
    patched = anchor + MODULE_EXCLUSIONS
    if patched not in text:
        if text.count(anchor) != 1:
            raise ValueError("The pinned module blacklist anchor changed")
        script.write_text(text.replace(anchor, patched, 1))
    zvbi = source / "vlc/contrib/src/zvbi/rules.mak"
    text = zvbi.read_text()
    anchor = "ifdef HAVE_ANDROID\n# discard bogus pthread_cancel calls\n"
    patched = ("ifdef HAVE_ANDROID\n"
               "# Android has no Linux V4L capture or pthread cancellation API.\n"
               "ZVBICONF += --disable-v4l\n# discard bogus pthread_cancel calls\n")
    if patched not in text:
        if text.count(anchor) != 1:
            raise ValueError("The pinned ZVBI Android block changed")
        zvbi.write_text(text.replace(anchor, patched, 1))


def verify_archive(source):
    manifest = json.loads((source / "build-source-manifest.json").read_text())
    expected_refs = {"libvlcjni": "a8d53a9151d7e4a9a5dfd0a5eb1cd92669afdc21",
                     "vlc": "c84ef1eda4f14f8b57a5b266b51c843cf51ed28b"}
    if manifest["source_refs"] != expected_refs or not manifest["files"]:
        raise ValueError("Archive source manifest does not match the pinned revisions")
    for name, expected in manifest.get("prepared_files", manifest["files"]).items():
        path = (source / name).resolve()
        if source.resolve() not in path.parents:
            raise ValueError("Source manifest file escapes the extracted tree")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Extracted source file differs from its archive: " + name)


def record_prepared(source):
    path = source / "build-source-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["prepared_files"] = {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in manifest["files"]
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-archive", action="store_true")
    parser.add_argument("--record-prepared", action="store_true")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    if args.verify_archive:
        verify_archive(args.source)
    elif args.record_prepared:
        record_prepared(args.source)
    else:
        prepare(args.source)
