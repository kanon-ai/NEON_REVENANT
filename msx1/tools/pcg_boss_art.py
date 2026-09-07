"""Original native SCREEN 2 art for the DAWN EXODUS giant battleship.

This file draws geometry on a 128 x 96 pixel canvas and expands each pixel
to a 2 x 2 cluster. It does not resize or sample the concept illustration.
The offline two-colour resolver enforces the TMS9918 8 x 1 colour rule.
Runtime receives the same 16-phase PCG contract as the existing worlds.

generate_frames(state=0) returns uint8 [16,192,256]. State bits 0 and 1
describe destroyed left/right cannon pods; state 3 opens the central hatch.
phase_metadata() returns physical screen coordinates, including hull motion.
HUD strips are blank; the runtime supplies the player, shots and HUD.
"""
from pathlib import Path
import json

import numpy as np
from PIL import Image, ImageDraw

from pcg_art import PALETTE, _two_colors


# Half-resolution shifts: eight-native-pixel steps reuse identical hull PCGs
# by moving their name-table placement. The bridge moves every phase and
# cannon barrels independently recoil by two pixels between these steps.
HULL_MOTION = ((0, 0),) * 4 + ((4, 0),) * 4 + ((0, -4),) * 4 + ((-4, 0),) * 4


def _recoil(phase, side):
    return -1 if (phase + side * 6) % 16 in (2, 3, 4) else 0


def phase_metadata():
    """Coordinates use the physical 256 x 192 screen, not world units."""
    return [dict(phase=p, offset=[dx * 2, dy * 2],
                 left=[72 + dx * 2, 102 + dy * 2 + _recoil(p, 0) * 2],
                 right=[184 + dx * 2, 102 + dy * 2 + _recoil(p, 1) * 2],
                 core=[128 + dx * 2, 98 + dy * 2],
                 bounds=[20 + dx * 2, 26 + dy * 2,
                         236 + dx * 2, 124 + dy * 2])
            for p, (dx, dy) in enumerate(HULL_MOTION)]


def _background(phase):
    image = Image.new('L', (128, 96), 1)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 8, 127, 24), fill=4)
    draw.rectangle((0, 25, 127, 36), fill=13)
    draw.rectangle((0, 37, 127, 45), fill=9)
    draw.rectangle((0, 46, 127, 56), fill=11)
    # Sparse flat skyline: the sunrise belongs behind the ship, not behind
    # the hostile shots travelling down the dark foreground.
    for x, width, height in ((0, 7, 7), (9, 4, 11), (15, 8, 5),
                             (27, 5, 8), (97, 4, 9), (105, 9, 6),
                             (116, 3, 12), (121, 7, 8)):
        draw.rectangle((x, 57 - height, x + width, 58), fill=1)
    draw.rectangle((0, 57, 127, 87), fill=1)
    # Open suspension stays identify the bridge even with the centre hidden.
    for side in (-1, 1):
        def reflect(x):
            return 64 + side * x
        draw.line([(reflect(64), 10), (reflect(49), 34),
                   (reflect(24), 55)], fill=1, width=2)
        draw.rectangle((min(reflect(46), reflect(49)), 30,
                        max(reflect(46), reflect(49)), 61), fill=1)
        draw.line((reflect(46), 32, reflect(46), 53), fill=6)
        for d, bottom in ((58, 53), (53, 54), (38, 56)):
            draw.line((reflect(d), 24 + (64-d), reflect(d), bottom), fill=1)
        draw.line((reflect(13), 57, reflect(64), 86), fill=10, width=1)
        draw.line((reflect(19), 57, reflect(64), 77), fill=6, width=1)
        # Perspective repetition with periodic positions: every phase moves.
        for k in range(7):
            z = ((k * 16 + phase) % 112) / 112.0
            depth = 3 + int(z * z * 34)
            y = 56 + depth
            if y >= 88:
                continue
            x = 12 + int(depth * 1.64)
            width = max(2, depth // 4)
            a, b = sorted((reflect(x), reflect(x + width)))
            draw.rectangle((a, y - max(1, depth // 6), b, y), fill=1)
            draw.line((a, y - max(1, depth // 6), b, y - max(1, depth // 6)), fill=10)
            draw.line((reflect(x), y - max(1, depth // 6), reflect(x), y), fill=6)
        for k in range(5):
            z = ((k * 24 + phase * 2) % 120) / 120.0
            depth = 6 + int(z * z * 34)
            y = 55 + depth
            if y > 85:
                continue
            x = int(6 + depth * 0.80)
            a, b = sorted((reflect(x), reflect(x + max(1, depth // 8))))
            draw.line((a, y, b, y), fill=6, width=max(1, depth // 15))
    return image


def _ship(image, phase, state):
    draw = ImageDraw.Draw(image)
    dx, dy = HULL_MOTION[phase]
    def poly(points, color, outline=None):
        draw.polygon([(x+dx, y+dy) for x, y in points], fill=color,
                     outline=outline)
    def line(points, color, width=1):
        draw.line([(x+dx, y+dy) for x, y in points], fill=color, width=width)
    def rect(box, color):
        x0, y0, x1, y1 = box
        draw.rectangle((x0+dx, y0+dy, x1+dx, y1+dy), fill=color)

    # Whole black mass establishes one coherent silhouette before details.
    poly([(10,46),(19,40),(35,34),(43,27),(54,24),(58,18),(61,17),
          (61,13),(67,13),(67,17),(70,18),(74,24),(85,27),(93,34),
          (109,40),(118,46),(117,51),(108,54),(103,61),(92,62),
          (86,59),(78,62),(50,62),(42,59),(36,62),(25,61),
          (20,54),(11,51)], 1)
    # Large armour planes. Local edge lights are purple, never player cyan.
    poly([(12,45),(36,35),(47,27),(56,26),(48,38),(38,43),(28,48),(12,48)], 16)
    poly([(116,45),(92,35),(81,27),(72,26),(80,38),(90,43),(100,48),(116,48)], 16)
    line([(13,45),(38,36),(48,28),(54,27)], 5)
    line([(115,45),(90,36),(80,28),(74,27)], 5)
    poly([(37,35),(48,29),(56,28),(52,35),(48,41),(39,41)], 1)
    poly([(91,35),(80,29),(72,28),(76,35),(80,41),(89,41)], 1)
    poly([(42,34),(48,31),(52,31),(48,37),(42,38)], 4)
    poly([(86,34),(80,31),(76,31),(80,37),(86,38)], 4)
    # Centre command tower sits clearly above the long wings.
    poly([(54,27),(58,20),(61,18),(67,18),(70,20),(74,27),(70,31),(58,31)], 4)
    line([(57,25),(71,25)], 5)
    rect((59,21,69,24), 1)
    for x in (60,64,68):
        rect((x,22,x+1,23), 8)
    line([(64,13),(64,18)], 5)
    rect((64,13,64,14), 9)
    for x in (45,83):
        line([(x,23),(x,28)], 1)
        rect((x,23,x,24), 9)
    # Mirrored lower shoulder facets frame the hatch instead of filling it
    # with noisy decoration. Repeated seam geometry shares many PCG tiles.
    poly([(48,33),(58,33),(56,41),(51,47),(47,54),(42,52),(42,43)], 16)
    poly([(80,33),(70,33),(72,41),(77,47),(81,54),(86,52),(86,43)], 16)
    line([(48,34),(57,34),(55,41),(50,47)], 5)
    line([(80,34),(71,34),(73,41),(78,47)], 5)
    poly([(43,43),(49,43),(46,50),(47,58),(42,58)], 4)
    poly([(85,43),(79,43),(82,50),(81,58),(86,58)], 4)
    rect((44,49,47,56), 1)
    rect((81,49,84,56), 1)
    rect((44,56,46,56), 8)
    rect((82,56,84,56), 8)
    # Black-bordered, octagonal cannon pods remain legible at native size.
    for side, (center, destroyed) in enumerate(((36, bool(state & 1)), (92, bool(state & 2)))):
        poly([(center-7,41),(center+5,41),(center+9,46),(center+8,57),
              (center+3,61),(center-5,61),(center-10,57),(center-10,47)], 1)
        poly([(center-6,42),(center+4,42),(center+7,46),(center+6,56),
              (center+2,59),(center-4,59),(center-8,55),(center-8,48)], 16)
        line([(center-6,43),(center+3,43),(center+6,46)], 5)
        retract = _recoil(phase, side) if not destroyed else 0
        poly([(x, y + retract) for x, y in
              [(center-4,47),(center+3,47),(center+6,50),(center+5,55),
               (center+2,57),(center-4,57),(center-6,54),(center-6,50)]], 1)
        line([(x, y + retract) for x, y in
              [(center-5,50),(center-3,48),(center+2,48),(center+4,50)]], 13)
        if destroyed:
            poly([(center-3,49),(center+3,49),(center+4,54),
                  (center-2,56),(center-5,53)], 1)
            line([(center-3,52),(center,50),(center+3,54)], 6)
            rect((center-2,54,center,55), 8)
        else:
            rect((center-2,50+retract,center+1,52+retract), 8)
            rect((center-1,50+retract,center,51+retract), 9)
    # Wing-tip vents are small red accents, not additional aim targets.
    for start in (16,104):
        rect((start,45,start+7,48), 1)
        for x in (start+1,start+4,start+7):
            rect((x,46,x,47), 13)
    # Central hatch: broad closed armour initially; exposed compact reactor
    # is explicitly a separate state, not a flashing fake vulnerability.
    poly([(57,37),(71,37),(78,47),(77,55),(70,61),(58,61),
          (51,55),(50,47)], 1)
    poly([(57,39),(71,39),(75,47),(74,54),(69,58),(59,58),
          (54,54),(53,47)], 4)
    line([(57,39),(71,39),(75,47)], 5)
    line([(54,54),(59,58),(69,58),(74,54)], 5)
    line([(64,40),(64,56)], 1)
    line([(57,46),(62,46),(62,51),(57,51)], 1)
    line([(71,46),(66,46),(66,51),(71,51)], 1)
    rect((61,42,67,43), 1)
    for x in (61,64,67):
        rect((x,42,x+1,42), 8)
    if state == 3:
        # The reactor opens inside a compact 24x24 native-pixel region.
        # Its frame remains shared with closed armour for resident PCG reuse.
        rect((58,44,69,55), 1)
        poly([(61,45),(66,45),(68,48),(68,51),(65,54),
              (62,54),(59,51),(59,48)], 8)
        poly([(62,47),(65,47),(66,49),(65,52),(62,52),
              (61,50),(61,48)], 10)
        rect((62,48,65,50), 11 if phase % 8 < 4 else 10)
    line([(56,61),(72,61)], 4)


def generate_frames(state=0):
    """Return deterministic legal native frames for one boss damage state."""
    if state not in (0, 1, 2, 3):
        raise ValueError('state must be the two-bit destroyed-pod mask 0..3')
    frames = []
    for phase in range(16):
        image = _background(phase)
        _ship(image, phase, state)
        native = np.repeat(np.repeat(np.array(image), 2, axis=0), 2, axis=1)
        yy, xx = np.indices(native.shape)
        # Broad blue/black material gives the fixed-palette ship dark facets
        # against the dawn, with no invented dark-blue hardware colour.
        shade = native == 16
        native[shade] = np.where((xx[shade] + yy[shade]) % 2 == 0, 4, 1)
        native[:16] = native[176:] = 1
        frames.append(native)
    return _two_colors(np.stack(frames).astype(np.uint8))


def write_preview(output):
    """Write native images and codec evidence; never writes existing assets."""
    from compile_boss import compile_boss
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    frames = generate_frames()
    np.save(output / 'boss-frames.npy', frames)
    palette = np.array(PALETTE, dtype=np.uint8)
    images = [Image.fromarray(palette[f]) for f in frames]
    images[0].save(output / 'boss-native.png')
    images[0].resize((768,576), Image.Resampling.NEAREST).save(output / 'boss-preview.png')
    enlarged = [im.resize((768,576), Image.Resampling.NEAREST) for im in images]
    enlarged[0].save(output / 'boss-loop.gif', save_all=True,
                     append_images=enlarged[1:], duration=100, loop=0, optimize=False)
    Image.fromarray(palette[generate_frames(3)[0]]).resize(
        (768,576), Image.Resampling.NEAREST).save(output / 'boss-core-open.png')
    (output / 'boss-targets.json').write_text(json.dumps(phase_metadata(), indent=2)+'\n', encoding='utf-8')
    font = Path(__file__).resolve().parents[1] / 'assets/source/font.bin'
    manifest = compile_boss([frames, *[generate_frames(s) for s in (1, 2, 3)]],
                            output / 'codec', font)
    summary = {key: manifest[key] for key in ('bands', 'max_packet_bytes', 'max_part_transfer_bytes', 'verification')}
    summary['base_bytes'] = 16384 + sum(p['bytes'] for p in manifest['phases'])
    summary['total_bytes'] = manifest['total_asset_bytes']
    summary['state_verification'] = manifest['state_verification']
    summary['static_regions'] = manifest['static_regions']
    (output / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'work/giant-boss-art')
    write_preview(parser.parse_args().output)
