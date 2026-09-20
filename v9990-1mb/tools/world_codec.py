"""Bank-streamable LZSS for the resident V9990 perspective animation.

Each output frame is exactly FRAME_BYTES bytes. A frame starts a fresh flags
group; low flag bits are consumed first. Zero means one literal byte; one
means a little-endian match word: ((length - 3) << 11) | (distance - 1).
Matches are 3..34 bytes with a 1..2048-byte backward distance. A match cannot
cross an output-frame boundary. History DOES continue across frames. There
is no terminator, embedded length, or padding between compressed frames.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import random

FRAME_BYTES = 256 * 180 // 2
FRAME_COUNT = 16
ATLAS_FRAME_BYTES = 8192
ATLAS_FRAME_COUNT = 10
FEATURE_FRAME_BYTES = 8192
WINDOW = 2048
MAX_MATCH = 34


def compress(data: bytes, frame_bytes: int = FRAME_BYTES, max_chain: int = 128) -> bytes:
    """Encode complete frames; never silently pad source artwork."""
    if frame_bytes <= 0 or not data or len(data) % frame_bytes:
        raise ValueError("input must contain one or more complete output frames")
    chains: dict[int, deque[int]] = defaultdict(deque)
    result = bytearray()
    position = 0

    def key_at(offset: int) -> int:
        return data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16)

    while position < len(data):
        frame_end = position + frame_bytes
        while position < frame_end:
            flag_position = len(result)
            result.append(0)
            flags = 0
            for bit in range(8):
                if position == frame_end:
                    break
                best_length, best_distance = 0, 0
                limit = min(MAX_MATCH, frame_end - position)
                if limit >= 3:
                    candidates = chains.get(key_at(position))
                    if candidates:
                        oldest = position - WINDOW
                        while candidates and candidates[0] < oldest:
                            candidates.popleft()
                        for count, candidate in enumerate(reversed(candidates)):
                            if count == max_chain:
                                break
                            if best_length and data[candidate + best_length] != data[position + best_length]:
                                continue
                            length = 3
                            while length < limit and data[candidate + length] == data[position + length]:
                                length += 1
                            if length > best_length:
                                best_length = length
                                best_distance = position - candidate
                                if length == limit:
                                    break
                consumed = best_length if best_length >= 3 else 1
                if best_length >= 3:
                    flags |= 1 << bit
                    token = ((best_length - 3) << 11) | (best_distance - 1)
                    result.extend((token & 255, token >> 8))
                else:
                    result.append(data[position])
                for offset in range(position, position + consumed):
                    if offset + 2 < len(data):
                        candidates = chains[key_at(offset)]
                        oldest = offset - WINDOW
                        while candidates and candidates[0] < oldest:
                            candidates.popleft()
                        candidates.append(offset)
                position += consumed
            result[flag_position] = flags
    return bytes(result)


def decompress(stream: bytes, frame_bytes: int = FRAME_BYTES,
               frame_count: int = FRAME_COUNT) -> bytes:
    """Strict reference decoder, including truncation and frame-bound checks."""
    if frame_bytes <= 0 or frame_count <= 0:
        raise ValueError("frame dimensions must be positive")
    output = bytearray()
    cursor = 0

    def take() -> int:
        nonlocal cursor
        if cursor >= len(stream):
            raise ValueError("truncated compressed world")
        value = stream[cursor]
        cursor += 1
        return value

    for _ in range(frame_count):
        frame_end = len(output) + frame_bytes
        while len(output) < frame_end:
            flags = take()
            for bit in range(8):
                if len(output) == frame_end:
                    break
                if flags & (1 << bit):
                    token = take() | (take() << 8)
                    distance = (token & 2047) + 1
                    length = (token >> 11) + 3
                    if distance > min(WINDOW, len(output)):
                        raise ValueError("match refers to uninitialized history")
                    if len(output) + length > frame_end:
                        raise ValueError("match crosses output-frame boundary")
                    for _ in range(length):
                        output.append(output[-distance])
                else:
                    output.append(take())
    if cursor != len(stream):
        raise ValueError("compressed world has unused trailing bytes")
    return bytes(output)


compress_world = compress
decompress_world = decompress


def decompress_banked(rom: bytes, bank: int, offset: int, frame_bytes: int,
                      frame_count: int, compressed_bytes: int) -> tuple[bytes, dict]:
    """Independent model of the native ASCII8 reader and E800h history ring.

    The ordinary decoder refers backward into its complete output. This one
    retains only the native 2048-byte ring, advances a 6000h..7FFFh source
    pointer, and switches banks exactly as world_read does. Its checks are
    build-time validation; the Z80 trusts the verified ROM byte stream.
    """
    if not 0 <= offset < 8192 or bank < 0 or frame_bytes <= 0 or frame_count <= 0:
        raise ValueError('invalid banked stream dimensions')
    cursor = 0x6000+offset
    consumed = position = crossings = matches = overlaps = ring_wraps = 0
    history = bytearray(WINDOW)
    output = bytearray()

    def take():
        nonlocal bank, cursor, consumed, crossings
        address = bank*8192+cursor-0x6000
        if consumed >= compressed_bytes or not 0 <= address < len(rom):
            raise ValueError('truncated banked stream')
        value = rom[address]
        consumed += 1
        cursor += 1
        if cursor == 0x8000:
            cursor = 0x6000
            bank += 1
            crossings += 1
        return value

    def emit(value):
        nonlocal position, ring_wraps
        history[position] = value
        output.append(value)
        position = (position+1) & 2047
        if position == 0:
            ring_wraps += 1

    for _ in range(frame_count):
        remaining = frame_bytes
        while remaining:
            flags = take()
            mask = 1
            while mask and remaining:
                if flags & mask:
                    token = take() | (take() << 8)
                    length, distance = (token >> 11)+3, (token & 2047)+1
                    if distance > min(WINDOW, len(output)):
                        raise ValueError('banked match refers to uninitialized history')
                    if length > remaining:
                        raise ValueError('banked match crosses output-frame boundary')
                    source = (position-distance) & 2047
                    matches += 1
                    overlaps += int(distance < length)
                    for _ in range(length):
                        emit(history[source])
                        source = (source+1) & 2047
                    remaining -= length
                else:
                    emit(take())
                    remaining -= 1
                mask = (mask << 1) & 255
    if consumed != compressed_bytes:
        raise ValueError('banked stream has unused trailing bytes')
    return bytes(output), dict(consumed_bytes=consumed, output_bytes=len(output),
                               source_bank_crossings=crossings, history_wraps=ring_wraps,
                               matches=matches, overlapping_matches=overlaps,
                               final_bank=bank, final_window_address=cursor)


def self_test() -> list[dict]:
    rng = random.Random(0x9990)
    cases = [
        ("single-byte", bytes([0xA5]), 1),
        ("max-overlap-run", bytes([0x22]) * (FRAME_BYTES * 2), FRAME_BYTES),
        ("two-byte-overlap", b"\x05\xF0" * (FRAME_BYTES), FRAME_BYTES),
        ("literal-and-partial-flags", bytes(range(251)) * 9, 251),
        ("window-edge", bytes(rng.randrange(256) for _ in range(2048)) * 4, 2048),
        ("incompressible", bytes(rng.randrange(256) for _ in range(FRAME_BYTES)), FRAME_BYTES),
        ("multiple-frame-boundaries", bytes((n * 37 + n // 91) & 255 for n in range(17 * 37)), 37),
        ("atlas-ten-frames", bytes((n // 23+n // 1297) & 255 for n in range(ATLAS_FRAME_BYTES*ATLAS_FRAME_COUNT)), ATLAS_FRAME_BYTES),
        ("feature-strip", bytes((n*71+n // 233) & 255 for n in range(FEATURE_FRAME_BYTES)), FEATURE_FRAME_BYTES),
    ]
    report = []
    for name, source, frame_bytes in cases:
        packed = compress(source, frame_bytes)
        decoded = decompress(packed, frame_bytes, len(source) // frame_bytes)
        if decoded != source:
            raise AssertionError(name)
        # Starting immediately before a bank boundary exercises flag, literal
        # and two-byte token crossings at several byte alignments.
        models = []
        for offset in (0, 8189, 8190, 8191):
            placed = bytes(8192+offset)+packed+bytes(8192)
            modeled, stats = decompress_banked(placed, 1, offset, frame_bytes,
                                               len(source)//frame_bytes, len(packed))
            assert modeled == source, (name, offset)
            models.append(stats)
        report.append({"case": name, "source_bytes": len(source), "packed_bytes": len(packed),
                       "banked_alignments": [0, 8189, 8190, 8191],
                       "banked_models": models, "passed": True})
    for name, packed, length in [
        ("reject-truncated-literal", b"\x00", 1),
        ("reject-uninitialized-match", b"\x01\x00\x00", 3),
        ("reject-frame-crossing", b"\x02\x11\x00\xF8", 3),
        ("reject-trailing-data", b"\x00\x11\x22", 1),
    ]:
        try:
            decompress(packed, length, 1)
        except ValueError:
            report.append({"case": name, "passed": True})
        else:
            raise AssertionError(name)
        try:
            decompress_banked(bytes(8191)+packed, 0, 8191, length, 1, len(packed))
        except ValueError:
            pass
        else:
            raise AssertionError(name+' (banked decoder)')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("destination", nargs="?", type=Path)
    parser.add_argument("--frame-bytes", type=int, default=FRAME_BYTES)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps({"tests": self_test()}, indent=2))
        return
    if args.source is None or args.destination is None:
        parser.error("source and destination are required unless --self-test is used")
    source = args.source.read_bytes()
    packed = compress(source, args.frame_bytes)
    assert decompress(packed, args.frame_bytes, len(source) // args.frame_bytes) == source
    args.destination.write_bytes(packed)
    print(json.dumps({"source_bytes": len(source), "packed_bytes": len(packed),
                      "ratio": round(len(packed) / len(source), 6),
                      "source_sha256": hashlib.sha256(source).hexdigest(),
                      "packed_sha256": hashlib.sha256(packed).hexdigest(),
                      "round_trip": True}, indent=2))


if __name__ == "__main__":
    main()
