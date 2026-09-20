"""V9958 RGB3 palette, preserving the original semantic color order."""
PALETTE_RGB3 = [
    (0,0,0),(0,0,1),(0,1,1),(1,2,2),
    (2,3,3),(1,5,5),(4,6,6),(7,7,7),
    (1,0,1),(3,3,4),(4,2,4),(7,3,4),
    (2,1,1),(6,3,1),(7,5,2),(7,6,4),
]
PALETTE = [tuple(round(c*255/7) for c in rgb) for rgb in PALETTE_RGB3]
PALETTE_RGB8 = PALETTE
