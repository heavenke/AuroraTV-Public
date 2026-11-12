"""Capture hashes and ELF build identity for final rebuilt LibVLC artifacts."""
import hashlib
import json
import re
import struct
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
NATIVE = PROJECT / "artifacts/vlc-lgpl-build/native"
OUTPUT = PROJECT / "artifacts/oss-public-sources/rebuilt-libvlc/native-fingerprints.json"
ROWS = []


def sha256(data):
    return hashlib.sha256(data).hexdigest()


for abi in ("arm64-v8a", "armeabi-v7a"):
    for filename in ("libvlc.so", "libvlcjni.so", "libc++_shared.so"):
        file = NATIVE / abi / filename
        data = file.read_bytes()
        if data[:4] != b"\x7fELF" or data[5] != 1:
            raise ValueError(f"Unexpected ELF format in {file}")
        bits = data[4]
        if bits == 2:
            header = struct.unpack_from("<16sHHIQQQIHHHHHH", data)
            program_format = "<IIQQQQQQ"
        else:
            header = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
            program_format = "<IIIIIIII"
        program_offset, program_size, program_count = header[5], header[9], header[10]
        loads, notes = [], []
        for index in range(program_count):
            item = struct.unpack_from(program_format, data, program_offset + index * program_size)
            kind = item[0]
            offset, size = (item[2], item[5]) if bits == 2 else (item[1], item[4])
            if kind == 1:
                loads.append({"offset": offset, "file_size": size, "alignment": item[-1],
                              "sha256": sha256(data[offset:offset + size])})
            if kind == 4:
                cursor, end = offset, offset + size
                while cursor + 12 <= end:
                    namesz, descsz, notetype = struct.unpack_from("<III", data, cursor)
                    cursor += 12
                    name = data[cursor:cursor + namesz].rstrip(b"\0")
                    cursor += (namesz + 3) & ~3
                    description = data[cursor:cursor + descsz]
                    cursor += (descsz + 3) & ~3
                    if name == b"GNU" and notetype == 3:
                        notes.append(description.hex())
        vlc_versions = sorted(set(v.decode("ascii") for v in re.findall(rb"4\.0\.0-dev-[0-9]+-g[0-9a-f]+", data)))
        ROWS.append({"abi": abi, "name": filename, "size": len(data), "sha256": sha256(data),
                     "elf_class": 64 if bits == 2 else 32, "elf_machine": header[2],
                     "gnu_build_ids": notes, "load_segments": loads, "vlc_version_strings": vlc_versions})

OUTPUT.write_text(json.dumps({
    "source_refs": {"libvlcjni": "a8d53a9151d7e4a9a5dfd0a5eb1cd92669afdc21",
                    "vlc": "c84ef1eda4f14f8b57a5b266b51c843cf51ed28b"},
    "scope": "final SDK native artifacts after GPL plugin blacklist and relink; APK packaging may strip ELF metadata, so APK correspondence must be checked separately",
    "libraries": ROWS,
}, indent=2) + "\n", encoding="utf-8")
for row in ROWS:
    print(row["abi"], row["name"], row["size"], row["sha256"])
