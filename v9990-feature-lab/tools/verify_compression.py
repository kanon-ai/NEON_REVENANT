"""Lossless Feature Lab stream tests, bank crossings and 512 KiB capacity.

Without --rom this performs no compilation or emulator interaction. With
--rom it independently reads every compressed stream from the built ROM.
"""
from pathlib import Path
import argparse
import hashlib
import json

from world_codec import (compress, decompress, decompress_banked, self_test,
                         FRAME_BYTES, FRAME_COUNT, ATLAS_FRAME_BYTES,
                         ATLAS_FRAME_COUNT, FEATURE_FRAME_BYTES)

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sources():
    yield 'atlas', ROOT/'assets/vram.bin', ATLAS_FRAME_BYTES, ATLAS_FRAME_COUNT, 0x10000
    for stage in range(3):
        yield f'world-{stage+1}', ROOT/'assets/world'/f'stage-{stage+1}.bin', FRAME_BYTES, FRAME_COUNT, 0x24000
    if (ROOT/'assets/feature.bin').exists():
        yield 'feature', ROOT/'assets/feature.bin', FEATURE_FRAME_BYTES, 1, 0x7E000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, help='Validate the actual built ROM and its adjacent build-manifest.json')
    parser.add_argument('--baseline', type=Path, help='Optional original assets directory; atlas and all three 16-frame worlds must remain identical')
    parser.add_argument('--report', type=Path, default=ROOT/'outputs/compression-verification.json')
    args = parser.parse_args()
    tests = self_test()
    streams, payloads = [], []
    offset = 4*8192
    for name, path, frame_bytes, frame_count, vram_address in sources():
        raw = path.read_bytes()
        assert len(raw) == frame_bytes*frame_count, name
        packed = compress(raw, frame_bytes)
        assert decompress(packed, frame_bytes, frame_count) == raw, name
        entry = dict(name=name, raw_bytes=len(raw), compressed_bytes=len(packed),
                     rom_offset=offset, bank=offset//8192, offset=offset%8192,
                     frame_bytes=frame_bytes, frame_count=frame_count,
                     vram_address=vram_address, vram_end_exclusive=vram_address+len(raw),
                     raw_sha256=sha(raw), compressed_sha256=sha(packed), passed=True)
        if args.baseline and name != 'feature':
            baseline = args.baseline/path.relative_to(ROOT/'assets')
            assert raw == baseline.read_bytes(), f'Original artwork changed: {name}'
            entry['baseline_artwork_identical'] = True
        streams.append(entry); payloads.append((raw, packed)); offset += len(packed)
    candidate = bytes(4*8192)+b''.join(packed for _, packed in payloads)
    assert len(candidate) == offset <= 524288
    candidate += bytes([255])*(524288-len(candidate))
    for entry, (raw, _) in zip(streams, payloads):
        decoded, model = decompress_banked(candidate, entry['bank'], entry['offset'],
                                            entry['frame_bytes'], entry['frame_count'], entry['compressed_bytes'])
        assert decoded == raw, entry['name']
        entry['banked_model'] = model
    atlas = streams[0]
    feature = next((entry for entry in streams if entry['name'] == 'feature'), None)
    baseline_allocation = 4*8192+ATLAS_FRAME_BYTES*ATLAS_FRAME_COUNT+sum(
        entry['compressed_bytes'] for entry in streams if entry['name'].startswith('world-'))
    report = dict(passed=True, native_execution_tested=False, tests=tests, streams=streams,
                  rom_bytes=524288, reserved_boot_and_runtime_bytes=4*8192,
                  allocated_bytes=offset, free_bytes=524288-offset,
                  raw_atlas_baseline_allocated_bytes=baseline_allocation,
                  raw_atlas_baseline_free_bytes=524288-baseline_allocation,
                  atlas_saved_bytes=atlas['raw_bytes']-atlas['compressed_bytes'],
                  added_feature_bytes=feature['compressed_bytes'] if feature else 0,
                  net_free_bytes_gained=baseline_allocation-offset,
                  retained_constraints='Original atlas pixels, all three 16-phase worlds, original VRAM destinations, E800-EFFF history ring, E000-E7FF data and F300 stack. Runtime ROM reservation remains three banks.',
                  native_confirmation='Verify executed ROM SHA-256 first. Deinterleave GFX9000 VRAM as logical[0::2]=physical[:262144], logical[1::2]=physical[262144:]. Compare [10000,24000) with vram.bin and [24000,7E000) with each world after normal world_load(stage). Compare the complete feature [7E000,80000) immediately after feature_load, before cursor_init (for example, at the first gfx_cursor entry breakpoint). During ordinary play compare only [7E000,7FE00): the final 512 feature bytes are intentionally changed into hardware cursor attributes/patterns. Recheck the atlas and immutable feature prefix after world reloads.')
    if args.rom:
        rom = args.rom.read_bytes()
        manifest = json.loads((args.rom.parent/'build-manifest.json').read_text())
        assert len(rom) == 524288 and rom[:2] == b'AB'
        assert sha(rom) == manifest['sha256']
        assert manifest['allocated_bytes'] == offset
        manifest_entries = [manifest['atlas'], *manifest['worlds']]
        if feature:
            manifest_entries.append(manifest['feature'])
        assert len(manifest_entries) == len(streams)
        proofs = []
        for entry, linked, (raw, packed) in zip(streams, manifest_entries, payloads):
            for field in ('name', 'rom_offset', 'bank', 'offset', 'frame_bytes', 'frame_count',
                          'raw_sha256', 'compressed_sha256', 'raw_bytes', 'compressed_bytes',
                          'vram_address', 'vram_end_exclusive'):
                assert linked[field] == entry[field], (entry['name'], field)
            start = entry['rom_offset']
            assert rom[start:start+len(packed)] == packed
            decoded, proof = decompress_banked(rom, entry['bank'], entry['offset'],
                                               entry['frame_bytes'], entry['frame_count'], entry['compressed_bytes'])
            assert decoded == raw
            proofs.append(dict(name=entry['name'], passed=True, **proof))
        assert rom[offset:] == bytes([255])*(len(rom)-offset)
        report['actual_ROM'] = dict(file=args.rom.name, sha256=sha(rom), passed=True, streams=proofs)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key not in ('tests', 'streams', 'native_confirmation')}, indent=2))


if __name__ == '__main__':
    main()
