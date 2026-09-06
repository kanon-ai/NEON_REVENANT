"""MSX3 concept art direction: midnight metals, ice light and warm threats.

The order remains compatible with the V9990 4bpp renderer. Index zero is
transparent; opaque shadows always use a nonzero palette entry.
"""
PALETTE_RGB5 = [
    (0,0,0), (1,1,2), (2,3,5), (5,7,9),
    (7,11,13), (5,21,23), (16,27,27), (28,29,28),
    (4,3,5), (11,12,14), (16,11,17), (29,13,18),
    (10,6,5), (27,15,7), (30,23,11), (31,28,21),
]
PALETTE = [tuple(round(c*255/31) for c in rgb) for rgb in PALETTE_RGB5]
