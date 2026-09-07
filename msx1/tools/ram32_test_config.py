"""Shared locations for the two explicit 32 KiB native test machines."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT.parent / 'outputs/msx1/v1.3'
STANDARD = os.environ.get('MSX_VIDEO_STANDARD', 'ntsc').lower()
if STANDARD not in ('ntsc', 'pal'):
    raise ValueError('MSX_VIDEO_STANDARD must be ntsc or pal')
MACHINE = 'NEON_MSX1_RAM32_' + STANDARD.upper()
VDP = 'TMS9918A' if STANDARD == 'ntsc' else 'TMS9929A'
OUT = RELEASE / STANDARD
OUT.mkdir(parents=True, exist_ok=True)
STAGE_DURATIONS = (750, 1500, 1500, 1500, 1200)
TIMING_SETUP = ('set ::neon_fast_vram_count 0;'
                'proc neon_vram_timing_violation {} {incr ::neon_fast_vram_count};'
                'set VDP.too_fast_vram_access_callback neon_vram_timing_violation')
