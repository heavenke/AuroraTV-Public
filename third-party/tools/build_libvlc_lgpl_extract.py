"""Verify and extract the exact public source archives for a Git-free build."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath


ARCHIVES = {
    "libvlcjni": ("a8d53a9151d7e4a9a5dfd0a5eb1cd92669afdc21",
                  "1276535c9b73e971d125fefabdbc98e40385605c6f1dbc5b44c84c2d98a0f4d7"),
    "vlc": ("c84ef1eda4f14f8b57a5b266b51c843cf51ed28b",
            "f472021915507a7b99bbf111d6e997e7897249847a78b86bac0cfe175f776bf3"),
}


def extract(archive_dir, destination):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Extraction destination must be empty")
    # Validate both archives before creating any source tree.
    inputs = {}
    for project, (revision, expected) in ARCHIVES.items():
        path = archive_dir / (project + "-" + revision + ".tar.gz")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("Archive SHA-256 mismatch: " + str(path))
        inputs[project] = path
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"source_refs": {name: value[0] for name, value in ARCHIVES.items()},
                "archive_sha256": {name: value[1] for name, value in ARCHIVES.items()},
                "files": {}}
    for project, path in inputs.items():
        target = destination / "vlc" if project == "vlc" else destination
        target.mkdir(parents=True, exist_ok=True)
        with tarfile.open(path, "r:gz") as archive:
            for entry in archive.getmembers():
                # Official source archives contain regular files and directories.
                parts = PurePosixPath(entry.name).parts
                if not parts or entry.name.startswith("/") or ".." in parts:
                    raise ValueError("Unsafe archive entry: " + entry.name)
                relative = PurePosixPath(*parts[1:])
                if str(relative) == ".":
                    continue
                output = target.joinpath(*relative.parts)
                if entry.isdir():
                    output.mkdir(parents=True, exist_ok=True)
                elif entry.isfile():
                    output.parent.mkdir(parents=True, exist_ok=True)
                    data = archive.extractfile(entry).read()
                    output.write_bytes(data)
                    output.chmod(entry.mode & 0o777)
                    key = output.relative_to(destination).as_posix()
                    manifest["files"][key] = hashlib.sha256(data).hexdigest()
                else:
                    raise ValueError("Unsupported source archive entry: " + entry.name)
    (destination / "build-source-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verified pinned source tree extracted into " + str(destination))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_dir", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    extract(args.archive_dir, args.destination)
