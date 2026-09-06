"""Cyclic SCREEN 2 PCG allocation and two-part, active-safe VRAM packets.

compile_stage(frames, stage, output_dir, font) accepts (16,192,256) uint8
palette-index frames. `stage` is used literally in filenames. Packet p changes
phase (p-1)%16 into p; packet 0 is the wraparound transition. Files are not
padded to 8 KiB. Runtime must apply A, then B, copy 640 name bytes into the
inactive name page, and flip name pages. No visible PCG is overwritten.
"""
from pathlib import Path
import hashlib
import heapq
import json
import struct
import numpy as np

PHASES = 16
CAPACITIES = (192, 256, 192)
FRAME_BUDGETS = (96, 128, 96)
NAMES = (0x3800, 0x3C00)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _encode(tile):
    pattern, color = bytearray(8), bytearray(8)
    for y in range(8):
        values = sorted(set(map(int, tile[y])))
        if len(values) > 2:
            raise ValueError(f"SCREEN 2 row has {len(values)} colors: {values}")
        bg, fg = values[0], values[-1]
        pattern[y] = sum((1 << (7-x)) for x in range(8)
                         if fg != bg and int(tile[y, x]) == fg)
        color[y] = (fg << 4) | bg
    return bytes(pattern + color)


def _bits(bits):
    while bits:
        bit = bits & -bits
        yield bit.bit_length() - 1
        bits ^= bit


def _color_graph(masks, capacity):
    """DSATUR on simultaneous/adjacent phase conflicts, including 15 <-> 0."""
    count = len(masks)
    phase_nodes = [0] * PHASES
    for node, mask in enumerate(masks):
        for phase in _bits(mask):
            phase_nodes[phase] |= 1 << node
    neighbors = []
    for node, mask in enumerate(masks):
        adjacent = 0
        for phase in _bits(mask):
            adjacent |= (phase_nodes[(phase-1) % PHASES] | phase_nodes[phase]
                         | phase_nodes[(phase+1) % PHASES])
        neighbors.append(adjacent & ~(1 << node))
    degree = [n.bit_count() for n in neighbors]
    colors, saturation = [-1] * count, [0] * count
    heap = [(0, -degree[v], -masks[v].bit_count(), v) for v in range(count)]
    heapq.heapify(heap)
    for _ in range(count):
        while True:
            neg_sat, _, _, node = heapq.heappop(heap)
            if colors[node] < 0 and -neg_sat == saturation[node].bit_count():
                break
        blocked = saturation[node]
        free_bit = (~blocked) & (blocked + 1)
        slot = free_bit.bit_length() - 1
        if slot >= capacity:
            raise ValueError(f"DSATUR needs more than {capacity} PCG slots; "
                             "reduce art tile budgets or alter frame reuse")
        colors[node] = slot
        for other in _bits(neighbors[node]):
            if colors[other] < 0 and not saturation[other] & free_bit:
                saturation[other] |= free_bit
                heapq.heappush(heap, (-saturation[other].bit_count(),
                                     -degree[other], -masks[other].bit_count(), other))
    for node, adjacent in enumerate(neighbors):
        assert all(colors[node] != colors[x] for x in _bits(adjacent))
    return colors


def _band_tiles(frames, band):
    tiles, lookup, masks, layouts = [], {}, [], []
    first, last = max(2, band*8), min(22, band*8+8)
    for phase, frame in enumerate(frames):
        layout = []
        for ty in range(first, last):
            row = []
            for tx in range(32):
                key = _encode(frame[ty*8:ty*8+8, tx*8:tx*8+8])
                if key not in lookup:
                    lookup[key] = len(tiles)
                    tiles.append(key)
                    masks.append(0)
                node = lookup[key]
                masks[node] |= 1 << phase
                row.append(node)
            layout.append(row)
        layouts.append(layout)
    unique = [len({n for row in f for n in row}) for f in layouts]
    if max(unique) > FRAME_BUDGETS[band]:
        raise ValueError(f"Band {band} exceeds per-frame tile budget "
                         f"{FRAME_BUDGETS[band]}: {unique}")
    colors = _color_graph(masks, CAPACITIES[band])
    requirements = [[-1] * CAPACITIES[band] for _ in range(PHASES)]
    for node, mask in enumerate(masks):
        for phase in _bits(mask):
            assert requirements[phase][colors[node]] < 0
            requirements[phase][colors[node]] = node
    initial = []
    for slot in range(CAPACITIES[band]):
        # Last requirement on the circular timeline ending at phase zero.
        initial.append(next((requirements[p][slot] for p in [0, *range(15, 0, -1)]
                             if requirements[p][slot] >= 0), -1))
    return dict(tiles=tiles, masks=masks, layouts=layouts, colors=colors,
                requirements=requirements, initial=initial,
                report=dict(band=band, distinct_tiles=len(tiles),
                            per_phase_unique=unique, frame_budget=FRAME_BUDGETS[band],
                            allocated_slots=max(colors)+1, slot_capacity=CAPACITIES[band],
                            adjacent_union=[sum(bool(m & ((1 << p) | (1 << ((p-1) % 16))))
                                                for m in masks) for p in range(16)]))


def _merge(records):
    merged = []
    for address, data in sorted(records):
        if merged and merged[-1][0] + len(merged[-1][1]) == address:
            merged[-1] = (merged[-1][0], merged[-1][1] + data)
        else:
            merged.append((address, data))
    return merged


def _split(records):
    total = sum(len(data) for _, data in records)
    remaining = min(total, (total + 640 + 1) // 2)
    a, b = [], []
    for address, data in records:
        n = min(remaining, len(data))
        if n:
            a.append((address, data[:n]))
            remaining -= n
        if n < len(data):
            b.append((address+n, data[n:]))
    return a, b


def _stream(records):
    return b''.join(struct.pack('<HH', address, len(data)) + data
                    for address, data in records) + bytes(4)


def parse_packet(packet):
    """Strict independent consumer of the published byte-stream contract."""
    if len(packet) < 652 or len(packet) > 8192:
        raise ValueError('Invalid packet length')
    part_b, names = struct.unpack_from('<HH', packet)
    if not 4 < part_b < names or names + 640 != len(packet):
        raise ValueError('Invalid packet section offsets')
    result = []
    for start, end in [(4, part_b), (part_b, names)]:
        records, pos = [], start
        while True:
            if pos + 4 > end:
                raise ValueError('Truncated stream header')
            address, size = struct.unpack_from('<HH', packet, pos)
            pos += 4
            if not size:
                if address != 0 or pos != end:
                    raise ValueError('Invalid stream terminator')
                break
            if pos + size > end:
                raise ValueError('Truncated stream payload')
            records.append((address, packet[pos:pos+size]))
            pos += size
        result.append(records)
    return result[0], result[1], packet[names:names+640]


def decode_screen(vram, name_base):
    """SCREEN 2 pixel decoder; intentionally does not use encoder tile keys."""
    pixels = np.empty((192, 256), dtype=np.uint8)
    for y in range(192):
        band = y // 64
        for column in range(32):
            code = vram[name_base + (y//8)*32 + column]
            offset = band*2048 + code*8 + y % 8
            bits, colors = vram[offset], vram[8192 + offset]
            for x in range(8):
                pixels[y, column*8+x] = colors >> 4 if bits & (128 >> x) else colors & 15
    return pixels


def _active_slots(vram, page):
    return [{vram[NAMES[page] + ty*32 + tx]
             for ty in range(max(2, band*8), min(22, band*8+8)) for tx in range(32)}
            for band in range(3)]


def _apply_safe(vram, records, active):
    for address, data in records:
        for dest, value in enumerate(data, address):
            pcg = dest if 0 <= dest < 0x1800 else dest-0x2000 if 0x2000 <= dest < 0x3800 else -1
            if pcg < 0:
                raise AssertionError(f'Non-PCG write at {dest:04X}')
            band, within = divmod(pcg, 2048)
            slot = within // 8
            assert slot < CAPACITIES[band], f'HUD font write at {dest:04X}'
            assert slot not in active[band], f'Active PCG write at {dest:04X}'
            vram[dest] = value


def verify_cycle(initial, packets, frames):
    vram, page = bytearray(initial), 0
    assert np.array_equal(decode_screen(vram, NAMES[page]), frames[0]), 'Initial picture mismatch'
    comparisons = 1
    for cycle in range(3):
        for previous in range(16):
            phase = (previous + 1) % 16
            a, b, names = parse_packet(packets[phase])
            active = _active_slots(vram, page)
            for part in (a, b):
                _apply_safe(vram, part, active)
                assert np.array_equal(decode_screen(vram, NAMES[page]), frames[previous]), 'Visible image corrupted during transfer'
                comparisons += 1
            inactive = 1-page
            vram[NAMES[inactive]+64:NAMES[inactive]+704] = names
            page = inactive
            assert np.array_equal(decode_screen(vram, NAMES[page]), frames[phase]), 'Completed picture mismatch'
            comparisons += 1
            for base in NAMES:
                assert vram[base:base+64] == bytes([192])*64
                assert vram[base+704:base+768] == bytes([192])*64
        assert vram[:0x3800] == initial[:0x3800], 'PCG cycle does not return to its initial steady state'
    return dict(passed=True, cycles=3, transitions=48, full_frame_comparisons=comparisons,
                active_slot_writes=0, protected_region_writes=0,
                steady_state_exact=True, phase_wraparound='15 -> 0 tested three times')


def compile_stage(frames, stage, output_dir, font):
    """Compile one stage; validate everything before creating output files.

    font is 512 bytes or a path to that file. Input HUD rows must be palette 1;
    runtime owns those rows, with character 192 representing a blank space.
    Returns a JSON-serializable manifest. Tile/color overflow raises ValueError.
    """
    frames = np.asarray(frames)
    if frames.shape != (16, 192, 256) or frames.dtype != np.uint8:
        raise ValueError('Expected uint8 frames with shape (16,192,256)')
    if np.any(frames > 15):
        raise ValueError('Palette indices must be between 0 and 15')
    if np.any(frames[:, :16] != 1) or np.any(frames[:, 176:] != 1):
        raise ValueError('HUD rows must be blank palette index 1')
    font = Path(font).read_bytes() if isinstance(font, (str, Path)) else bytes(font)
    if len(font) != 512 or font[:8] != bytes(8):
        raise ValueError('Expected 64 eight-byte glyphs, starting with blank space')
    bands = [_band_tiles(frames, band) for band in range(3)]
    vram = bytearray(16384)
    for band, info in enumerate(bands):
        for slot, node in enumerate(info['initial']):
            if node < 0:
                continue
            offset = band*2048 + slot*8
            tile = info['tiles'][node]
            vram[offset:offset+8] = tile[:8]
            vram[8192+offset:8192+offset+8] = tile[8:]
        if band != 1:
            offset = band*2048 + 192*8
            vram[offset:offset+512] = font
            vram[8192+offset:8192+offset+512] = bytes([0xF1])*512
    phase_names = []
    for phase in range(PHASES):
        names = []
        for info in bands:
            names.extend(info['colors'][node] for row in info['layouts'][phase] for node in row)
        assert len(names) == 640
        phase_names.append(bytes(names))
    for base in NAMES:
        vram[base:base+768] = bytes([192])*64 + phase_names[0] + bytes([192])*64
    vram[0x3B00] = vram[0x3B80] = 208
    initial = bytes(vram)
    state = [info['initial'].copy() for info in bands]
    packets, stats = [None]*16, [None]*16
    for phase in [*range(1, 16), 0]:
        records, changed_slots = [], []
        for band, info in enumerate(bands):
            changed = 0
            for slot, node in enumerate(info['requirements'][phase]):
                if node < 0 or node == state[band][slot]:
                    continue
                assert info['requirements'][(phase-1) % 16][slot] < 0
                offset = band*2048 + slot*8
                tile = info['tiles'][node]
                old = info['tiles'][state[band][slot]] if state[band][slot] >= 0 else bytes(16)
                if tile[:8] != old[:8]:
                    records.append((offset, tile[:8]))
                if tile[8:] != old[8:]:
                    records.append((8192+offset, tile[8:]))
                state[band][slot] = node
                changed += 1
            changed_slots.append(changed)
        a, b = _split(_merge(records))
        sa, sb = _stream(a), _stream(b)
        part_b, names_offset = 4+len(sa), 4+len(sa)+len(sb)
        packet = struct.pack('<HH', part_b, names_offset) + sa + sb + phase_names[phase]
        if len(packet) > 8192:
            raise ValueError(f'Stage {stage}, phase {phase}: packet is {len(packet)} bytes, exceeds 8192')
        packets[phase] = packet
        a_bytes, b_bytes = sum(len(d) for _, d in a), sum(len(d) for _, d in b)
        stats[phase] = dict(phase=phase, from_phase=(phase-1) % 16,
                            file=f'phase-{stage}-{phase:02}.bin', bytes=len(packet), sha256=_sha(packet),
                            part_b_offset=part_b, names_offset=names_offset,
                            part_a_records=len(a), part_b_records=len(b),
                            part_a_transfer_bytes=a_bytes, part_b_pcg_bytes=b_bytes,
                            part_b_transfer_bytes=b_bytes+640, names_bytes=640,
                            changed_slots_by_band=changed_slots)
    assert state == [info['initial'] for info in bands]
    verification = verify_cycle(initial, packets, frames)
    report = dict(stage=stage, format='SCREEN2 cyclic PCG, 16 phases, two-part streams',
                  input_sha256=_sha(frames.tobytes()), font_sha256=_sha(font),
                  initial=dict(file=f'world-{stage}.bin', bytes=len(initial), sha256=_sha(initial)),
                  bands=[info['report'] for info in bands], phases=stats,
                  max_packet_bytes=max(s['bytes'] for s in stats),
                  max_part_transfer_bytes=max(max(s['part_a_transfer_bytes'], s['part_b_transfer_bytes']) for s in stats),
                  verification=verification)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out/report['initial']['file']).write_bytes(initial)
    for info, packet in zip(stats, packets):
        (out/info['file']).write_bytes(packet)
    (out/f'codec-manifest-{stage}.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frames', type=Path)
    parser.add_argument('stage', type=int)
    parser.add_argument('output', type=Path)
    parser.add_argument('--font', type=Path, required=True)
    args = parser.parse_args()
    manifest = compile_stage(np.load(args.frames), args.stage, args.output, args.font)
    print(json.dumps({k: manifest[k] for k in ['stage', 'bands', 'max_packet_bytes',
                                               'max_part_transfer_bytes', 'verification']}, indent=2))
