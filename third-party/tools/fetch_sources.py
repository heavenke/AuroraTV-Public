"""Fetch pinned upstream archives into an ignored cache and prepare the SDK build tree."""

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]


def safe_path(root, relative):
    parts = PurePosixPath(relative).parts
    if not parts or relative.startswith("/") or "\\" in relative or ":" in relative or ".." in parts:
        raise ValueError("Unsafe manifest path")
    output = root.joinpath(*parts).resolve()
    output.relative_to(root.resolve())
    return output


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path, entry):
    if path.stat().st_size != entry["size"] or sha256(path) != entry["sha256"]:
        raise ValueError("Source archive checksum mismatch: " + entry["path"])


def download(url, target, entry):
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".download-", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AuroraTV-public-third-party-sources"})
        with os.fdopen(descriptor, "wb") as output, urllib.request.urlopen(request, timeout=60) as source:
            shutil.copyfileobj(source, output, 1024 * 1024)
        verify(temporary, entry)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def fetch(entry, cache, baseline, verified_baselines):
    target = safe_path(cache, entry["path"])
    if target.is_file():
        verify(target, entry)
        return target
    for url in entry.get("urls", []):
        try:
            download(url, target, entry)
            return target
        except (OSError, ValueError, urllib.error.URLError):
            print("Upstream archive unavailable or changed; trying the pinned baseline copy: " + entry["path"])
    bundle = safe_path(cache, "baseline-1112-source-bundle.zip")
    if bundle not in verified_baselines:
        if bundle.exists():
            verify(bundle, baseline)
        else:
            download(baseline["url"], bundle, baseline)
        verified_baselines.add(bundle)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".baseline-", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output, zipfile.ZipFile(bundle) as archive:
            with archive.open(entry["baseline_member"]) as source:
                shutil.copyfileobj(source, output, 1024 * 1024)
        verify(temporary, entry)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache")
    parser.add_argument("--all", action="store_true", help="Fetch contrib and NDK runtime source archives too")
    parser.add_argument("--prepare-build", type=Path, help="Create an empty pinned LibVLC build tree, including contrib tarballs")
    args = parser.parse_args()
    index = json.loads((ROOT / "archive-index.json").read_text(encoding="utf-8"))
    cache = args.cache.resolve()
    verified_baselines = set()
    selected = [entry for entry in index["archives"] if entry["group"] == "core" or args.all or args.prepare_build]
    for entry in selected:
        fetch(entry, cache, index["baseline_bundle"], verified_baselines)
        print("Verified " + entry["path"])
    if args.prepare_build:
        spec = importlib.util.spec_from_file_location("libvlc_extract", ROOT / "tools/build_libvlc_lgpl_extract.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        destination = args.prepare_build.resolve()
        module.extract(cache / "archives", destination)
        tarballs = destination / "vlc/contrib/tarballs"
        tarballs.mkdir(parents=True, exist_ok=True)
        for entry in selected:
            if entry["group"] == "contrib":
                shutil.copyfile(safe_path(cache, entry["path"]), tarballs / Path(entry["path"]).name)
        sidecars = ROOT / "materials/baseline-1112/rebuilt-libvlc/contrib-source-archives"
        if sidecars.exists():
            for sidecar in sidecars.glob("*.githash"):
                shutil.copyfile(sidecar, tarballs / sidecar.name)
        print("Prepared pinned build inputs in " + str(destination))


if __name__ == "__main__":
    main()
