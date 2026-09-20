"""TMS9918-specific two-colour PCGs for the new coast and dawn environments."""
from pathlib import Path
from pcg_art import _source_frames,_approximate
ROOT=Path(__file__).resolve().parents[1]
def generate_frames(stage):
    assert stage in (0,4)
    return _approximate(_source_frames(1 if stage==0 else 3,ROOT/'assets/campaign-source',2),512)
