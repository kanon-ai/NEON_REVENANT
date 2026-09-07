"""Compile four damage states over one cyclic SCREEN 2 boss animation.

State zero uses the normal two-part PCG stream. Every tile differing in a
damage state receives a permanent slot above that band's normal allocation.
The runtime changes only the usual 640 name bytes, so damage does not require
an extra VRAM transfer, a second PCG stream, or a RAM decompression buffer.
All four states share the same animation phase and background geometry.
"""
from pathlib import Path
import hashlib
import json
import tempfile
from types import FunctionType

import numpy as np

import pcg_codec as codec


STATES = 4
SCENE = 5
BOSS_FRAME_BUDGETS = (96, 192, 96)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _compile_base(frames, output, font):
    """Reuse the codec with a boss-only middle-band art budget.

    The normal 128-tile limit reserves room for fully changing adjacent
    scenery. Most of this hull persists across phases, so it may use 192
    distinct middle-band tiles provided the *same* conflict allocator fits
    their adjacent phases into the physical 256 slots. Bind private copies
    of the two functions to private globals: no codec globals, other worlds,
    physical slot capacities, or transfer safety checks are modified.
    """
    band_globals = dict(codec._band_tiles.__globals__)
    band_globals['FRAME_BUDGETS'] = BOSS_FRAME_BUDGETS
    band_allocator = FunctionType(codec._band_tiles.__code__, band_globals,
                                  codec._band_tiles.__name__)
    stage_globals = dict(codec.compile_stage.__globals__)
    stage_globals['_band_tiles'] = band_allocator
    compiler = FunctionType(codec.compile_stage.__code__, stage_globals,
                            codec.compile_stage.__name__)
    return compiler(frames, SCENE, output, font)


def _decode(vram, page):
    """Independent vectorized SCREEN 2 decoder for exhaustive state checks."""
    memory = np.frombuffer(vram, dtype=np.uint8)
    y, x = np.indices((192, 256))
    names = memory[codec.NAMES[page] + (y // 8) * 32 + x // 8]
    offset = (y // 64) * 2048 + names.astype(np.uint16) * 8 + y % 8
    patterns, colors = memory[offset], memory[8192 + offset]
    return np.where(patterns & (128 >> (x % 8)), colors >> 4, colors & 15)


def _set_names(vram, page, names):
    start = codec.NAMES[page] + 64
    vram[start:start + 640] = names


def _verify(initial, packets, frames, names, regions):
    """Test every phase and damage-state pair, including intermediate writes."""
    # Cross-check the faster exhaustive decoder against the existing decoder.
    for page in (0, 1):
        assert np.array_equal(_decode(initial, page),
                              codec.decode_screen(initial, codec.NAMES[page]))
    snapshots, vram, page = {}, bytearray(initial), 0
    snapshots[0] = bytes(vram)
    for phase in range(1, 16):
        a, b, packet_names = codec.parse_packet(packets[phase])
        active = codec._active_slots(vram, page)
        for part in (a, b):
            codec._apply_safe(vram, part, active)
        page = 1 - page
        _set_names(vram, page, packet_names)
        snapshots[phase] = bytes(vram)

    # A future change to the base allocator must never touch resident states.
    protected = set()
    for region in regions:
        for address in (region['pattern_address'], region['color_address']):
            protected.update(range(address, address + region['bytes_per_table']))
    for packet in packets:
        for part in codec.parse_packet(packet)[:2]:
            for address, data in part:
                if not protected.isdisjoint(range(address, address + len(data))):
                    raise AssertionError('Base packet overwrites resident damage tiles')

    comparisons = transitions = same_phase = 0
    for previous in range(16):
        phase = (previous + 1) % 16
        a, b, _ = codec.parse_packet(packets[phase])
        for before in range(STATES):
            for after in range(STATES):
                # Every state can be displayed before or after either part.
                vram, page = bytearray(snapshots[previous]), 0
                _set_names(vram, page, names[before][previous])
                assert np.array_equal(_decode(vram, page), frames[before][previous]), 'Previous state mismatch'
                comparisons += 1
                active = codec._active_slots(vram, page)
                for part in (a, b):
                    codec._apply_safe(vram, part, active)
                    assert np.array_equal(_decode(vram, page), frames[before][previous]), 'Damage state corrupted during PCG transfer'
                    comparisons += 1
                page = 1 - page
                _set_names(vram, page, names[after][phase])
                assert np.array_equal(_decode(vram, page), frames[after][phase]), 'Completed damage state mismatch'
                comparisons += 1
                transitions += 1
                for base in codec.NAMES:
                    assert vram[base:base+64] == bytes([192])*64
                    assert vram[base+704:base+768] == bytes([192])*64
                for region in regions:
                    for start in (region['pattern_address'], region['color_address']):
                        end = start + region['bytes_per_table']
                        assert vram[start:end] == initial[start:end]
                # A name-only state change at an unchanged phase is also safe.
                vram = bytearray(snapshots[previous])
                _set_names(vram, 0, names[before][previous])
                _set_names(vram, 1, names[after][previous])
                assert np.array_equal(_decode(vram, 1), frames[after][previous]), 'Same-phase damage state mismatch'
                comparisons += 1
                same_phase += 1

    # Long sequential cycles exercise retained unused slots, rather than
    # relying solely on isolated snapshots of the canonical PCG timeline.
    vram, page, state = bytearray(initial), 0, 0
    for step in range(48):
        previous, phase = step % 16, (step + 1) % 16
        after = (step * 3 + step // 4) % STATES
        a, b, _ = codec.parse_packet(packets[phase])
        active = codec._active_slots(vram, page)
        for part in (a, b):
            codec._apply_safe(vram, part, active)
            assert np.array_equal(_decode(vram, page), frames[state][previous])
            comparisons += 1
        page = 1 - page
        _set_names(vram, page, names[after][phase])
        assert np.array_equal(_decode(vram, page), frames[after][phase])
        comparisons += 1
        state = after
        if phase == 0:
            assert vram[:0x3800] == initial[:0x3800], 'Damage-state PCG cycle does not return to initial state'
    return dict(passed=True, state_pair_transitions=transitions,
                same_phase_state_pairs=same_phase, sequential_transitions=48,
                full_frame_comparisons=comparisons, active_slot_writes=0,
                protected_region_writes=0, static_tile_writes_after_initial=0,
                arbitrary_state_changes=True, phase_wraparound='All 16 state pairs plus three sequential cycles',
                steady_state_exact=True)


def compile_boss(frames_by_state, output_dir, font):
    """Return a JSON manifest and write world-5, phase-5, and damage names.

    frames_by_state is a mapping keyed by 0..3 or a four-element sequence.
    Each element must be uint8 [16,192,256], with blank HUD rows. Capacity,
    color legality and decoded pixels are validated before final files exist.
    The font contract is identical to pcg_codec.compile_stage.
    """
    frames = [np.asarray(frames_by_state[state]) for state in range(STATES)]
    for state, pictures in enumerate(frames):
        if pictures.shape != (16, 192, 256) or pictures.dtype != np.uint8:
            raise ValueError(f'State {state}: expected uint8 frames (16,192,256)')
        if np.any(pictures > 15):
            raise ValueError(f'State {state}: palette indices exceed 15')
        if np.any(pictures[:, :16] != 1) or np.any(pictures[:, 176:] != 1):
            raise ValueError(f'State {state}: HUD rows must be palette 1')

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.boss-codec-', dir=output) as temporary:
        temporary = Path(temporary)
        report = _compile_base(frames[0], temporary, font)
        initial = bytearray((temporary / report['initial']['file']).read_bytes())
        packets = [(temporary / p['file']).read_bytes() for p in report['phases']]
        base_names = [codec.parse_packet(packet)[2] for packet in packets]
        names = [[bytearray(data) for data in base_names] for _ in range(STATES)]
        regions, state_changes = [], [[0]*16 for _ in range(STATES)]
        for band, info in enumerate(report['bands']):
            start_slot = info['allocated_slots']
            variants = {}
            first, last = max(2, band*8), min(22, band*8+8)
            for state in range(1, STATES):
                for phase in range(16):
                    for ty in range(first, last):
                        for tx in range(32):
                            rect = (slice(ty*8, ty*8+8), slice(tx*8, tx*8+8))
                            base_tile = codec._encode(frames[0][phase][rect])
                            tile = codec._encode(frames[state][phase][rect])
                            if tile == base_tile:
                                continue
                            if tile not in variants:
                                variants[tile] = start_slot + len(variants)
                            slot = variants[tile]
                            # Defer overflow until the complete exact demand is
                            # known, so the artist gets actionable capacity data.
                            if slot < codec.CAPACITIES[band]:
                                names[state][phase][(ty-2)*32+tx] = slot
                            state_changes[state][phase] += 1
            total = start_slot + len(variants)
            if total > codec.CAPACITIES[band]:
                raise ValueError(f'Boss band {band}: {start_slot} base slots + '
                                 f'{len(variants)} resident damage slots = {total}, '
                                 f'capacity {codec.CAPACITIES[band]}; reduce damage '
                                 'region complexity or the number of hull poses')
            for tile, slot in variants.items():
                offset = band*2048 + slot*8
                initial[offset:offset+8] = tile[:8]
                initial[8192+offset:8192+offset+8] = tile[8:]
            region = dict(band=band, first_slot=start_slot, slots=len(variants),
                          pattern_address=band*2048+start_slot*8,
                          color_address=8192+band*2048+start_slot*8,
                          bytes_per_table=len(variants)*8,
                          allocated_with_states=total, capacity=codec.CAPACITIES[band])
            regions.append(region)
        initial = bytes(initial)
        names = [[bytes(data) for data in state] for state in names]
        verification = _verify(initial, packets, frames, names, regions)
        # Retain the existing codec's independent three-cycle proof as well.
        base_verification = codec.verify_cycle(initial, packets, frames[0])
        artifacts = {report['initial']['file']: initial}
        artifacts.update((p['file'], data) for p, data in zip(report['phases'], packets))
        name_entries, distinct_names = [], {}
        for state in range(1, STATES):
            for phase, data in enumerate(names[state]):
                if data not in distinct_names:
                    filename = f'boss-name-{state}-{phase:02}.bin'
                    distinct_names[data] = filename
                    artifacts[filename] = data
                name_entries.append(dict(state=state, phase=phase,
                                         file=distinct_names[data], bytes=640,
                                         sha256=_sha(data)))
        report['initial']['sha256'] = _sha(initial)
        report.update(format='SCREEN2 cyclic PCG with permanent damage tiles and state-dependent names',
                      states=STATES, base_state=0, names=name_entries,
                      static_regions=regions,
                      state_input_sha256=[_sha(f.tobytes()) for f in frames],
                      state_changed_tiles=state_changes,
                      distinct_name_assets=len(distinct_names),
                      additional_names_bytes=sum(map(len, distinct_names)),
                      total_asset_bytes=sum(map(len, artifacts.values())),
                      state_verification=verification, verification=base_verification,
                      runtime_contract='Apply the selected phase packet A then B; copy the same phase names for damage state 0..3 into the inactive name page, then flip. State 0 names are inside the packet; other states use names[]. No runtime PCG writes outside these packets.')
        for filename, data in artifacts.items():
            (output / filename).write_bytes(data)
        (output / f'codec-manifest-{SCENE}.json').write_text(
            json.dumps(report, indent=2)+'\n', encoding='utf-8')
        return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--font', type=Path,
                        default=Path(__file__).resolve().parents[1]/'assets/source/font.bin')
    args = parser.parse_args()
    from pcg_boss_art import generate_frames
    result = compile_boss([generate_frames(state) for state in range(STATES)],
                          args.output, args.font)
    print(json.dumps({key: result[key] for key in
                      ('static_regions', 'distinct_name_assets', 'total_asset_bytes',
                       'max_part_transfer_bytes', 'state_verification')}, indent=2))
