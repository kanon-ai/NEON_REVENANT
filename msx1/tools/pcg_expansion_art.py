"""Original coastal approach and dawn escape for the MSX1 PCG edition.

Only these two worlds are generated here. Geometry is projected offline with
an opaque depth buffer; the Z80 receives the same sixteen-frame PCG contract
as the three preserved worlds. All moving structures repeat every 384 world
units, including the phase 15 -> 0 camera step.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

PERIOD = 384.0
NEAR, FAR = 24.0, 2304.0
FOCAL, EYE, HORIZON = 130.0, 76.0, 57.0


def _clip(points):
    for plane, sign in ((NEAR, 1), (FAR, -1)):
        result = []
        for a, b in zip(points, points[1:] + points[:1]):
            inside_a = (a[2] - plane) * sign >= 0
            inside_b = (b[2] - plane) * sign >= 0
            if inside_a:
                result.append(a)
            if inside_a != inside_b:
                t = (plane - a[2]) / (b[2] - a[2])
                result.append(tuple(a[k] + t * (b[k] - a[k]) for k in range(3)))
        points = result
        if not points:
            break
    return points


class Scene:
    def __init__(self, stage, phase):
        self.stage, self.phase, self.faces = stage, phase, []

    def face(self, points, material):
        points = _clip(points)
        if len(points) >= 3:
            self.faces.append((points, material))

    def ground(self, x0, x1, z0, z1, material, y=0):
        self.face([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], material)

    def side(self, x, y0, y1, z0, z1, material):
        self.face([(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)], material)

    def front(self, x0, x1, y0, y1, z, material):
        self.face([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], material)

    def box(self, x0, x1, y0, y1, z0, z1, front=1, side=2, top=4):
        self.front(x0, x1, y0, y1, z0, front)
        self.side(x0 if x0 > 0 else x1, y0, y1, z0, z1, side)
        self.ground(x0, x1, z0, z1, top, y1)

    def route(self):
        dawn = self.stage == 4
        self.ground(-1000, 1000, NEAR, FAR, 16 if dawn else 15, -24)
        self.ground(-78, 78, NEAR, FAR, 0)
        self.ground(-64, 64, NEAR, FAR, 8 if dawn else 1, .1)
        for side in (-1, 1):
            lo, hi = sorted((side * 72, side * 83))
            self.ground(lo, hi, NEAR, FAR, 3 if dawn else 2, 2)
            self.side(side * 83, -26, 2, NEAR, FAR, 0)
            self.ground(*sorted((side * 80, side * 83)), NEAR, FAR, 10 if dawn else 4, 3)
        for k in range(-4, 30):
            z = k * 96 - self.phase
            self.ground(-2, 2, z + 19, z + 52, 11 if dawn else 4, .2)
            for side in (-1, 1):
                self.ground(*sorted((side * 61, side * 64)), z + 63, z + 81,
                            10 if dawn else 6, .3)
                # Solid parapet blocks and their top planes grow toward camera.
                a, b = sorted((side * 81, side * 90))
                self.box(a, b, 2, 17, z + 7, z + 35, 0, 8 if dawn else 2, 10 if dawn else 4)
            if dawn:
                # Torn joints and isolated chunks leave a visibly ruined deck.
                self.face([(-64, .4, z + 78), (-13, .4, z + 82),
                           (9, .4, z + 74), (61, .4, z + 88),
                           (61, .4, z + 91), (6, .4, z + 78),
                           (-15, .4, z + 85), (-64, .4, z + 81)], 0)
            else:
                # Long sparse sea streaks pass outward, unlike a static backdrop.
                for j in range(4):
                    x = -120 - j * 93
                    self.ground(x - 23, x + 37, z + 25 + j * 11,
                                z + 29 + j * 11, 4 if j == 0 else 2, -23.7)

    def harbor(self):
        for repeat in range(-2, 8):
            z = repeat * PERIOD - self.phase
            # An asymmetric, broad refinery mass leaves the seaward half open.
            self.box(119, 235, -22, 91, z + 18, z + 199, 1, 2, 4)
            self.box(143, 220, 91, 115, z + 49, z + 159, 0, 3, 4)
            self.side(118.5, 41, 48, z + 28, z + 180, 4)
            self.side(118.3, 44, 46, z + 35, z + 171, 6)
            self.side(118.4, 13, 19, z + 43, z + 102, 8)
            self.side(118.2, 15, 18, z + 46, z + 80, 10)
            for level in (61, 78):
                for off in (47, 95, 147):
                    self.side(118.4, level - 2, level + 6, z + off - 2, z + off + 16, 0)
                    self.side(118.2, level, level + 3, z + off, z + off + 11,
                              10 if (level + off) % 3 == 0 else 5)
            for off in (38, 109, 163):
                self.box(118, 128, 4, 91, z + off, z + off + 8, 0, 1, 4)
            # Twin chimney stacks, warm aviation lights and one high pipe gantry.
            for x, off, top in ((160, 66, 198), (202, 135, 164)):
                self.box(x, x + 17, 111, top, z + off, z + off + 22, 3, 1, 4)
                self.front(x - 2, x + 19, top - 19, top - 11, z + off - .2, 8)
                self.front(x + 5, x + 12, top, top + 4, z + off - .3, 10)
            # Cantilever crane silhouette: mast, crossarm and hanging hook.
            self.box(103, 113, 0, 169, z + 270, z + 283, 0, 2, 4)
            self.box(39, 166, 163, 175, z + 269, z + 284, 1, 0, 4)
            self.face([(108, 161, z + 269), (111, 166, z + 269),
                       (161, 188, z + 269), (158, 183, z + 269)], 4)
            self.front(47, 49, 110, 163, z + 269 - .2, 4)
            self.front(44, 54, 106, 110, z + 269 - .3, 10)
            # A faceted round storage tank with a domed cap distinguishes the
            # refinery from another street of rectangular office buildings.
            rings = ((0, 36), (74, 36), (79, 36), (99, 36),
                     (114, 31), (124, 19), (128, 0))
            for level, ((y0, r0), (y1, r1)) in enumerate(zip(rings, rings[1:])):
                for face in range(12):
                    a, b = face * math.tau / 12, (face + 1) * math.tau / 12
                    points = [(172 + math.cos(a) * r0, y0, z + 253 + math.sin(a) * r0),
                              (172 + math.cos(b) * r0, y0, z + 253 + math.sin(b) * r0),
                              (172 + math.cos(b) * r1, y1, z + 253 + math.sin(b) * r1),
                              (172 + math.cos(a) * r1, y1, z + 253 + math.sin(a) * r1)]
                    self.face(points, 4 if level == 1 or level >= 4 else (1, 2, 4, 2)[(face // 3) % 4])
            # Low seaward beacons retain a port silhouette without enclosing it.
            self.box(-106, -98, -22, 38, z + 182, z + 192, 0, 2, 4)
            self.front(-107, -97, 37, 42, z + 181.8, 6)

    def escape(self):
        for repeat in range(-2, 8):
            z = repeat * PERIOD - self.phase
            for side in (-1, 1):
                lo, hi = sorted((side * 109, side * 131))
                # Unequal broken portal towers, with broad dark side faces.
                top = 158 if side < 0 else 205
                self.box(lo, hi, -48, top, z + 88, z + 122, 0, 3, 10)
                lo2, hi2 = sorted((side * 102, side * 138))
                self.box(lo2, hi2, 107, 117, z + 86, z + 126, 8, 0, 10)
                inner = side * 108.8
                self.side(inner, 18, 102, z + 96, z + 108, 8)
                self.side(inner - side * .1, 41, 74, z + 98, z + 103, 10)
                # Diagonal cable/steel stays open toward the sunrise.
                self.face([(side * 116, top - 7, z + 103),
                           (side * 121, top - 7, z + 103),
                           (side * 91, 18, z + 331),
                           (side * 88, 18, z + 331)], 0)
                # Jagged remaining horizontal beams never close the whole sky.
                self.face([(side * 119, top - 14, z + 89),
                           (side * 52, top - 19, z + 89),
                           (side * 62, top - 10, z + 89),
                           (side * 44, top - 5, z + 89),
                           (side * 120, top + 1, z + 89)], 0)
                self.front(*sorted((side * 111, side * 124)), top + 1, top + 10, z + 94, 8)
            self.box(91, 111, 2, 28, z + 250, z + 287, 0, 8, 10)
            self.box(-101, -89, 2, 13, z + 291, z + 313, 0, 3, 10)

    def background(self, step):
        image = Image.new('L', (256 // step, 160 // step), 0)
        draw = ImageDraw.Draw(image)
        def rect(coords, value):
            draw.rectangle(tuple(round(v / step) for v in coords), fill=value)
        if self.stage == 0:
            rect((0, 27, 255, 66), 1)
            rect((0, 43, 255, 64), 2)
            # Tiny skyline across the bay, separated from foreground machinery.
            for k in range(19):
                x = k * 13 - 8
                top = 43 - (k * 19 % 17)
                rect((x, top, x + 5 + k % 6, 59), 1 if k % 3 else 0)
                if k % 5 == 1:
                    rect((x + 2, top - 7, x + 3, top), 2)
                    rect((x + 2, top + 6, x + 3, top + 8), 10)
            draw.ellipse(tuple(round(v / step) for v in (33, 9, 45, 21)), fill=5)
        else:
            # Ordered MSX palette bands give a warm open sky without RGB assets.
            rect((0, 0, 255, 20), 12)
            rect((0, 20, 255, 37), 13)
            rect((0, 37, 255, 51), 14)
            rect((0, 51, 255, 66), 11)
            draw.ellipse(tuple(round(v / step) for v in (114, 23, 150, 59)), fill=7)
            # Low survivor skyline keeps the sun and sky unobstructed.
            for k in range(22):
                x = k * 12 - 3
                top = 57 - (k * 7 % 10)
                rect((x, top, x + 5 + k % 5, 63), 8)
                if k % 4 == 0:
                    rect((x + 2, top - 4, x + 3, top), 8)
        return np.array(image, dtype=np.uint8)

    def render(self, step=2):
        self.route()
        (self.harbor if self.stage == 0 else self.escape)()
        width, height = 256 // step, 160 // step
        canvas = self.background(step)
        depth = np.full((height, width), np.inf, dtype=np.float64)
        for points, material in self.faces:
            p = np.asarray(points, dtype=np.float64)
            screen = np.column_stack(((128 + FOCAL * p[:, 0] / p[:, 2]) / step,
                                      (HORIZON + FOCAL * (EYE - p[:, 1]) / p[:, 2]) / step))
            for index in range(1, len(p) - 1):
                ids = [0, index, index + 1]
                v, z = screen[ids], p[ids, 2]
                x0, x1 = max(0, math.floor(v[:, 0].min())), min(width, math.ceil(v[:, 0].max()) + 1)
                y0, y1 = max(0, math.floor(v[:, 1].min())), min(height, math.ceil(v[:, 1].max()) + 1)
                if x0 >= x1 or y0 >= y1:
                    continue
                den = ((v[1, 1] - v[2, 1]) * (v[0, 0] - v[2, 0]) +
                       (v[2, 0] - v[1, 0]) * (v[0, 1] - v[2, 1]))
                if abs(den) < .000001:
                    continue
                yy, xx = np.mgrid[y0:y1, x0:x1]
                xx, yy = xx + .5, yy + .5
                a = ((v[1, 1] - v[2, 1]) * (xx - v[2, 0]) + (v[2, 0] - v[1, 0]) * (yy - v[2, 1])) / den
                b = ((v[2, 1] - v[0, 1]) * (xx - v[2, 0]) + (v[0, 0] - v[2, 0]) * (yy - v[2, 1])) / den
                c = 1 - a - b
                inv = a / z[0] + b / z[1] + c / z[2]
                d = np.divide(1, inv, out=np.full_like(inv, np.inf), where=inv > 0)
                current = depth[y0:y1, x0:x1]
                use = (a >= -.000001) & (b >= -.000001) & (c >= -.000001) & (d <= current + .01)
                canvas[y0:y1, x0:x1][use] = material
                current[use] = d[use]
        materials = np.repeat(np.repeat(canvas, step, axis=0), step, axis=1)
        # Material codes map to fixed TMS colors; dim surfaces keep opaque
        # black coverage. Dither stays fixed in screen space as in old worlds.
        basic = np.array([1, 4, 4, 13, 4, 5, 7, 15, 6, 8, 10, 11, 5, 13, 9, 4, 13], dtype=np.uint8)
        pixels = basic[materials]
        yy, xx = np.indices((160, 256))
        bayer = np.array([[0, 2], [3, 1]])[yy % 2, xx % 2]
        for material, foreground, background, coverage in ((1, 4, 1, 1), (2, 4, 1, 2),
                                                            (3, 13, 1, 2), (8, 6, 1, 2),
                                                            (12, 5, 4, 2)):
            mask = materials == material
            pixels[mask] = np.where(bayer[mask] < coverage, foreground, background)
        # Sparse horizontal water highlights distinguish the open bay from
        # the checker-dithered road and metal. Projected waves still advance.
        for material, color in ((15, 4), (16, 13)):
            mask = materials == material
            pixels[mask] = np.where((yy[mask] % 4 == 0) & (xx[mask] % 2 == 0), color, 1)
        return pixels


def source_frames(stage, step=2):
    if stage not in (0, 4):
        raise ValueError('Expansion stage must be 0 or 4')
    output = np.ones((16, 192, 256), dtype=np.uint8)
    for phase in range(16):
        output[phase, 16:176] = Scene(stage, phase * PERIOD / 16).render(step)
    # Camera displacement of one complete world period must produce the same
    # view independently of a modulo shortcut or a duplicated output frame.
    assert np.array_equal(Scene(stage, PERIOD).render(step), output[0, 16:176])
    return output
