"""Convert the authored V9990 environments to resident V9958 SCREEN 4 pages.

Run ``python tools/generate_world.py`` inside the standalone turboR project.
For the initial source import only, pass ``--import-source PATH_TO_V9990_PROJECT``.
The imported, unmodified source data is then sufficient for future rebuilds.

Each 16 KiB frame uses patterns at +0000, colors at +2000, and names at
+3800.  The +1800..1fff hole is reserved for global hardware sprite tables.
World pictures occupy y16..175. HUD rows use fixed ASCII32..95 glyphs in
pattern slots192..255 of the first and third 64-line bands.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from art_palette import PALETTE, PALETTE_RGB3

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source'
OUTPUT = ROOT / 'assets/world'
WIDTH, HEIGHT = 256, 192
SOURCE_HEIGHT = 180
FRAME_BYTES = 0x4000
SOURCE_FRAME_BYTES = 256 * 180 // 2
SOURCE_PHASES = tuple(range(0, 16, 2))
FONT_FIRST = 192
FONT_COLOR = 0x71
WORLD_TOP, WORLD_BOTTOM = 16, 176


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unpack_4bpp(raw: bytes, height: int) -> np.ndarray:
    packed = np.frombuffer(raw, dtype=np.uint8).reshape(height, 128)
    result = np.empty((height, 256), dtype=np.uint8)
    result[:, 0::2] = packed >> 4
    result[:, 1::2] = packed & 15
    return result


def import_source(source_root: Path) -> None:
    """Take read-only copies of the original world art and original glyph masks."""
    source_root = source_root.resolve()
    if source_root == ROOT:
        raise ValueError('Import from the separate V9990 project, not this port')
    (SOURCE / 'world').mkdir(parents=True, exist_ok=True)
    original_manifest = json.loads((source_root / 'assets/manifest.json').read_text())
    (SOURCE / 'palette.json').write_text(
        json.dumps({'palette_rgb8': original_manifest['palette_rgb8']}, indent=2) + '\n')
    source_atlas = (source_root / 'assets/vram.bin').read_bytes()
    atlas = unpack_4bpp(source_atlas, len(source_atlas) // 128)
    base_y = original_manifest['base'] // 128
    font = bytearray()
    for character in range(32, 96):
        x, y, width, height = original_manifest['sprites'][f'font_{character}']
        assert width <= 6 and height == 8
        # Preserve the original bitmap, adding one empty column on its left.
        glyph = np.zeros((8, 8), dtype=np.uint8)
        glyph[:, 1:width+1] = atlas[y-base_y:y-base_y+8, x:x+width] != 0
        font.extend(np.packbits(glyph, axis=1).tobytes())
    assert len(font) == 512 and not any(font[:8])
    (SOURCE / 'font.bin').write_bytes(font)
    copied = []
    for stage in range(1, 4):
        original = source_root / 'assets/world' / f'stage-{stage}.bin'
        target = SOURCE / 'world' / original.name
        shutil.copyfile(original, target)
        data = target.read_bytes()
        assert len(data) == SOURCE_FRAME_BYTES * 16
        copied.append({'file': f'world/{original.name}', 'bytes': len(data),
                       'sha256': sha256(data)})
    title_source = source_root / 'outputs/v1.2/title.png'
    if title_source.exists():
        shutil.copyfile(title_source, SOURCE / 'title.png')
        copied.append({'file': 'title.png', 'sha256': sha256(title_source.read_bytes())})
    (SOURCE / 'manifest.json').write_text(json.dumps({
        'origin': 'NEON REVENANT V9990 v1.2 authored assets',
        'source_format': '256x180, 16 frames, 4bpp, even pixels in high nibble',
        'files': copied, 'font_ascii': [32, 95],
        'font_bytes': len(font), 'font_sha256': sha256(font),
        'font_source_atlas_sha256': sha256(source_atlas),
        'font_placement': 'Original 6x8 mask, shifted right one pixel in an 8x8 tile',
    }, indent=2) + '\n')


def quantize_lines(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Find the least-error palette pair independently for every eight-pixel row.

    Exhaustive pair search in RGB uses perceptual channel weights 2:3:1.
    No spatial dither is added. Index zero is reserved for transparency;
    opaque world shadows use a nonzero color as in the source artwork.
    Returns reconstructed indices and the corresponding pattern/color bytes.
    """
    assert rgb.shape == (HEIGHT, WIDTH, 3)
    palette = np.asarray(PALETTE, dtype=np.float32)
    lines = rgb.reshape(-1, 8, 3).astype(np.float32)
    delta = lines[:, :, None, :] - palette[None, None, :, :]
    distance = (delta * delta * np.array([2, 3, 1], dtype=np.float32)).sum(axis=3)
    best_error = np.full(len(lines), np.inf, dtype=np.float32)
    best_a = np.ones(len(lines), dtype=np.uint8)
    best_b = np.ones(len(lines), dtype=np.uint8)
    for a in range(1, 16):
        for b in range(a, 16):
            error = np.minimum(distance[:, :, a], distance[:, :, b]).sum(axis=1)
            improved = error < best_error
            best_error[improved] = error[improved]
            best_a[improved], best_b[improved] = a, b
    rows = np.arange(len(lines))[:, None]
    columns = np.arange(8)[None, :]
    use_b = distance[rows, columns, best_b[:, None]] < distance[rows, columns, best_a[:, None]]
    indices = np.where(use_b, best_b[:, None], best_a[:, None]).astype(np.uint8)
    patterns = np.packbits(use_b, axis=1)[:, 0].reshape(HEIGHT, 32)
    colors = ((best_b << 4) | best_a).reshape(HEIGHT, 32)
    return indices.reshape(HEIGHT, WIDTH), patterns, colors, float(best_error.mean()/8)


def decode_frame(data: bytes) -> np.ndarray:
    """Independent SCREEN 4 table decoder used for exact output verification."""
    assert len(data) == FRAME_BYTES
    result = np.empty((HEIGHT, WIDTH), dtype=np.uint8)
    for tile_y in range(24):
        band = tile_y // 8
        for tile_x in range(32):
            tile = data[0x3800 + tile_y * 32 + tile_x]
            for row in range(8):
                offset = band * 2048 + tile * 8 + row
                pattern, color = data[offset], data[0x2000 + offset]
                for bit in range(8):
                    result[tile_y*8+row, tile_x*8+bit] = (
                        color >> 4 if pattern & (128 >> bit) else color & 15)
    return result


def encode_frame(rgb: np.ndarray, font: bytes, hud: bool) -> tuple[bytes, np.ndarray, dict]:
    target, patterns, colors, error = quantize_lines(rgb)
    frame = bytearray(FRAME_BYTES)
    counts = []
    for band in range(3):
        dictionary = {}
        limit = 192 if hud and band != 1 else 256
        for tile_y in range(8):
            screen_tile_y = band*8+tile_y
            if hud and screen_tile_y in (0, 1, 22, 23):
                start = 0x3800 + screen_tile_y*32
                frame[start:start+32] = bytes([FONT_FIRST])*32
                continue
            for tile_x in range(32):
                y = screen_tile_y * 8
                pattern = patterns[y:y+8, tile_x].tobytes()
                color = colors[y:y+8, tile_x].tobytes()
                key = pattern + color
                if key not in dictionary:
                    index = len(dictionary)
                    assert index < limit, f'Band {band} overflows the available tile slots'
                    dictionary[key] = index
                    start = band*2048 + index*8
                    frame[start:start+8] = pattern
                    frame[0x2000+start:0x2000+start+8] = color
                frame[0x3800 + screen_tile_y*32 + tile_x] = dictionary[key]
        counts.append(len(dictionary))
        if hud and band != 1:
            start = band*2048 + FONT_FIRST*8
            frame[start:start+512] = font
            frame[0x2000+start:0x2000+start+512] = bytes([FONT_COLOR])*512
    if hud:
        target[:WORLD_TOP] = 1
        target[WORLD_BOTTOM:] = 1
    decoded = decode_frame(bytes(frame))
    assert np.array_equal(decoded, target), 'SCREEN 4 pattern/color/name round trip failed'
    assert not any(frame[0x1800:0x2000]), 'Global sprite hole must remain reserved'
    assert not any(frame[0x3B00:0x4000]), 'Unused tail must remain zero'
    if hud:
        for band in (0, 2):
            start = band*2048+FONT_FIRST*8
            assert frame[start:start+512] == font
            assert frame[0x2000+start:0x2000+start+512] == bytes([FONT_COLOR])*512
    return bytes(frame), decoded, {'background_tiles_per_band': counts,
                                  'weighted_rgb_error_per_pixel': round(error, 3),
                                  'exact_table_round_trip': True,
                                  'reserved_holes_zero': True,
                                  'fixed_hud_glyphs_verified': hud}


def as_image(indices: np.ndarray) -> Image.Image:
    return Image.fromarray(np.asarray(PALETTE, dtype=np.uint8)[indices], 'RGB')


def port_title_labels(title: Image.Image, font: bytes) -> np.ndarray:
    """Keep the original title art, with clear native-port labels and start prompt."""
    rgb = np.array(title, dtype=np.uint8)
    glyphs = np.unpackbits(np.frombuffer(font, dtype=np.uint8)).reshape(64, 8, 8)

    def text(value: str, x: int, y: int) -> None:
        for offset, character in enumerate(value):
            mask = glyphs[ord(character)-32].astype(bool)
            patch = rgb[y:y+8, x+offset*6:x+offset*6+8]
            patch[mask] = PALETTE[7]

    rgb[:12] = PALETTE[1]
    text('MSX TURBO R / V9958', 4, 1)
    text('512K ROM', 200, 1)
    subtitle = 'V9958 NATIVE / TURBO R ONLY'
    rgb[78:89] = PALETTE[1]
    text(subtitle, (256-len(subtitle)*6)//2, 80)
    prompt = 'PRESS FIRE TO LAUNCH'
    rgb[167:179] = PALETTE[1]
    text(prompt, (256-len(prompt)*6)//2, 169)
    return rgb


def generate() -> dict:
    assert len(PALETTE_RGB3) == 16 and all(0 <= c <= 7 for rgb in PALETTE_RGB3 for c in rgb)
    assert PALETTE == [tuple(round(c*255/7) for c in rgb) for rgb in PALETTE_RGB3]
    font = (SOURCE / 'font.bin').read_bytes()
    assert len(font) == 512 and not any(font[:8])
    source_palette = np.array(json.loads((SOURCE / 'palette.json').read_text())['palette_rgb8'], dtype=np.uint8)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stages, stage_previews = [], []
    for stage in range(1, 4):
        raw = (SOURCE / 'world' / f'stage-{stage}.bin').read_bytes()
        assert len(raw) == 16*SOURCE_FRAME_BYTES
        frames, pictures, stats, indexed = [], [], [], []
        for source_phase in SOURCE_PHASES:
            begin = source_phase*SOURCE_FRAME_BYTES
            source_indices = unpack_4bpp(raw[begin:begin+SOURCE_FRAME_BYTES], SOURCE_HEIGHT)
            source_image = Image.fromarray(source_palette[source_indices], 'RGB')
            resized = source_image.resize((WIDTH, WORLD_BOTTOM-WORLD_TOP), Image.Resampling.LANCZOS)
            rgb = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)
            rgb[:] = PALETTE[1]
            rgb[WORLD_TOP:WORLD_BOTTOM] = np.asarray(resized)
            data, decoded, frame_stats = encode_frame(rgb, font, hud=True)
            frames.append(data); indexed.append(decoded); pictures.append(as_image(decoded))
            stats.append({'source_phase': source_phase, 'sha256': sha256(data), **frame_stats})
        packed = b''.join(frames)
        assert len(packed) == 131072 and len(set(frames)) == 8
        changes = [int(np.count_nonzero(indexed[i][WORLD_TOP:WORLD_BOTTOM] !=
                                       indexed[(i+1)%8][WORLD_TOP:WORLD_BOTTOM])) for i in range(8)]
        assert min(changes) > 0
        (OUTPUT / f'stage-{stage}.bin').write_bytes(packed)
        pictures[0].save(OUTPUT / f'stage-{stage}-native.png')
        pictures[0].resize((1024, 768), Image.Resampling.NEAREST).save(OUTPUT / f'stage-{stage}-preview.png')
        animated = [im.resize((512, 384), Image.Resampling.NEAREST) for im in pictures]
        animated[0].save(OUTPUT / f'stage-{stage}.gif', save_all=True, append_images=animated[1:],
                         duration=[70, 60, 70, 70, 60, 70, 70, 60], loop=0, optimize=False,
                         disposal=2)
        with Image.open(OUTPUT / f'stage-{stage}.gif') as gif:
            assert gif.n_frames == 8
            duration = 0
            for index in range(8):
                gif.seek(index)
                assert np.array_equal(np.asarray(gif.convert('RGB')), np.asarray(animated[index]))
                duration += gif.info['duration']
        record = {'stage': stage, 'raw_bytes': len(packed), 'sha256': sha256(packed),
                  'source_sha256': sha256(raw), 'source_phases': list(SOURCE_PHASES),
                  'unique_frames': 8, 'changed_pixels_per_frame': changes,
                  'gif_round_trip_frames': 8, 'gif_duration_ms': duration, 'frames': stats}
        stages.append(record); stage_previews.append(pictures)
        print(f'Stage {stage}: {len(packed)} bytes, 8 unique frames, table/GIF round trips passed', flush=True)
    contact = Image.new('RGB', (768, 576), PALETTE[1])
    for stage, pictures in enumerate(stage_previews):
        for row, phase in enumerate((0, 2, 4)):
            contact.paste(pictures[phase], (stage*256, row*192))
    contact.resize((1536, 1152), Image.Resampling.NEAREST).save(OUTPUT / 'contact-sheet.png')
    title_record = None
    if (SOURCE / 'title.png').exists():
        with Image.open(SOURCE / 'title.png') as original:
            assert original.size == (320, 240)
            title = original.convert('RGB').crop((32, 14, 288, 226)).resize((256, 192), Image.Resampling.LANCZOS)
        data, decoded, stats = encode_frame(port_title_labels(title, font), font, hud=False)
        (ROOT / 'assets/title.bin').write_bytes(data)
        as_image(decoded).save(ROOT / 'assets/title-native.png')
        as_image(decoded).resize((1024, 768), Image.Resampling.NEAREST).save(ROOT / 'assets/title-preview.png')
        title_record = {'raw_bytes': len(data), 'sha256': sha256(data), 'source_crop': [32, 14, 288, 226],
                        'native_labels': ['MSX TURBO R / V9958', 'V9958 NATIVE / TURBO R ONLY',
                                          'PRESS FIRE TO LAUNCH'], **stats}
        print('Title: 16384 bytes, table round trip passed', flush=True)
    manifest = {
        'format': 'V9958 SCREEN 4, 256x192, indexed 16-color palette, 2 colors per 8x1 pixels',
        'frame_bytes': FRAME_BYTES, 'frames_per_stage': 8, 'stage_bytes': 131072,
        'world_viewport': [0, WORLD_TOP, WIDTH, WORLD_BOTTOM],
        'source_dimensions': [256, 180], 'source_frames': 16, 'source_phases': list(SOURCE_PHASES),
        'background_rate_hz': 15, 'world_period': 384,
        'palette_rgb3': PALETTE_RGB3, 'palette_rgb8': PALETTE,
        'quantization': 'Exhaustive least-error 2-color pair per 8x1 pixels, RGB weights2:3:1, no dithering',
        'opaque_palette_indices': list(range(1, 16)),
        'layout': {'patterns_offset': 0, 'patterns_bytes': 6144,
                   'colors_offset': 8192, 'colors_bytes': 6144,
                   'name_table_offset': 14336, 'name_table_bytes': 768,
                   'reserved_sprite_hole_offset': 6144, 'reserved_sprite_hole_bytes': 2048},
        'hud': {'rows': [0, 1, 22, 23], 'font_bands': [0, 2], 'first_glyph_slot': FONT_FIRST,
                'ascii_range': [32, 95], 'font_colors': FONT_COLOR, 'initial_character': 'space'},
        'registers': {'R3': 255, 'R4': '(frame << 3) | 3', 'R10': 'frame',
                      'R2': '(frame << 4) | 14', 'R6': 3, 'R5': 183, 'R11': 0,
                      'sprite_pattern_address': 6144, 'sprite_color_address': 22528,
                      'sprite_attribute_address': 23040},
        'stages': stages, 'title': title_record,
        'total_world_bytes': sum(item['raw_bytes'] for item in stages),
        'total_with_title_bytes': sum(item['raw_bytes'] for item in stages)+(title_record['raw_bytes'] if title_record else 0),
    }
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-source', type=Path,
                        help='First-time read-only import from the original V9990 project')
    args = parser.parse_args()
    if args.import_source:
        import_source(args.import_source)
    generate()


if __name__ == '__main__':
    main()
