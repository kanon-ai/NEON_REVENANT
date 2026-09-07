"""Build five PCG worlds, preserving the original three scenes."""
from pathlib import Path
import json,os
import numpy as np
from PIL import Image
from pcg_art import generate_frames,PALETTE
from pcg_codec import compile_stage

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'
OUT=ROOT.parent/'outputs/msx1/v1.2'

def generate_worlds():
    OUT.mkdir(parents=True,exist_ok=True)
    quality=os.environ.get('NEON_PCG_QUALITY','high')
    reports=[]
    for stage in range(5):
        frames=generate_frames(stage,ASSETS/'source',quality)
        report=compile_stage(frames,stage,ASSETS,ASSETS/'source/font.bin')
        report['quality']=quality
        np.save(ASSETS/f'frames-{stage}.npy',frames)
        pictures=[Image.fromarray(np.asarray(PALETTE,dtype=np.uint8)[f]) for f in frames]
        pictures[0].resize((768,576),Image.Resampling.NEAREST).save(OUT/f'world-{stage+1}-reference.png')
        pictures[0].save(OUT/f'world-{stage+1}-reference.gif',save_all=True,append_images=pictures[1:],duration=67,loop=0)
        reports.append(report)
        print(f"Stage {stage+1}: {quality}, 16 PCG frames, max upload part {report['max_part_transfer_bytes']} bytes",flush=True)
    (ASSETS/'pcg-manifest.json').write_text(json.dumps({'quality':quality,'worlds':reports},indent=2)+'\n')
    return reports

if __name__=='__main__':generate_worlds()
