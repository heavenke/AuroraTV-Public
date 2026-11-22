"""Create source-free Annex-B fixtures for the isolated black-box CBS packet test."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct


def escaped(value: bytes) -> bytes:
    output = bytearray()
    zeroes = 0
    for byte in value:
        if zeroes >= 2 and byte <= 3:
            output.append(3)
            zeroes = 0
        output.append(byte)
        zeroes = zeroes + 1 if byte == 0 else 0
    return bytes(output)


def number(value: int) -> bytes:
    return b'\xff' * (value // 255) + bytes([value % 255])


def sei(messages: list[tuple[int, bytes]]) -> bytes:
    rbsp = b''.join(number(kind) + number(len(data)) + data for kind, data in messages) + b'\x80'
    return b'\x4e\x01' + escaped(rbsp)


def annexb(units: list[bytes]) -> bytes:
    return b''.join((b'\0\0\0\1' if i == 0 else b'\0\0\1') + value for i, value in enumerate(units))


def create(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    vcl = b'\x02\x01\x80'  # intentionally opaque: no slice reconstruction is required
    hdr = struct.pack('>8H2I', 13250, 34500, 7500, 3000, 34000, 16000, 15635, 16450, 10000000, 1)
    user = b'\xb5\0\x3c\0\0\1\0\0\3\1\0\0\2'
    valid = [(137, hdr), (144, b'\x03\xe8\x01\x90'), (4, user), (200, b'\0\0\1\0\0\3'),
             (147, b'\x12'), (147, b'\x10'), (147, b'\x01'), (147, b'\x02')]
    mixed = valid[:2] + [(147, b'\0')] + valid[2:5] + [(147, b'\3'), (147, b'\xff')] + valid[5:]
    cases = {
        'mixed-hdr-user-epb': (annexb([sei(mixed), vcl]), annexb([sei(valid), vcl]), True, False),
        'valid-hdr-sdr-transitions': (annexb([sei(valid), vcl]), None, False, False),
        'opaque-complex-sps': (annexb([b'\x42\x01\xff\0\0\3\1\x80', vcl]), None, False, False),
        'truncated-nal-header': (b'\0\0\1\x4e', None, False, False),
        'truncated-sei-payload': (annexb([b'\x4e\x01\x93\x05\0\x80', vcl]), None, False, False),
        'no-pseudo-eos-for-only-atc': (annexb([sei([(147, b'\0')])]), None, False, False),
        'suffix-sei-preserved': (annexb([b'\x50\x01' + escaped(b'\x93\x01\0\x80'), vcl]), None, False, False),
        'generic-options-still-reject': (b'\0\0\1\x4e', None, False, True),
    }
    manifest = []
    for name, (source, expected, changed, generic) in cases.items():
        (directory / f'{name}.hevc').write_bytes(source)
        (directory / f'{name}.expected.hevc').write_bytes(source if expected is None else expected)
        manifest.append({'name': name, 'changed': changed, 'generic': generic})
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    create(parser.parse_args().directory)
