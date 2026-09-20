from pathlib import Path
import json,numpy as np
from PIL import Image
from campaign_art import generate_frames
from pcg_art import PALETTE
from pcg_codec import compile_stage
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'assets';O=ROOT/'outputs'
manifest=json.loads((A/'pcg-manifest.json').read_text())
for stage in (0,4):
    f=generate_frames(stage);report=compile_stage(f,stage,A,A/'source/font.bin');report['quality']='high'
    np.save(A/f'frames-{stage}.npy',f)
    pics=[Image.fromarray(np.asarray(PALETTE,dtype=np.uint8)[x]) for x in f]
    pics[0].resize((768,576),Image.Resampling.NEAREST).save(O/f'world-{stage+1}-reference.png')
    pics[0].save(O/f'world-{stage+1}-reference.gif',save_all=True,append_images=pics[1:],duration=67,loop=0)
    manifest['worlds'][stage]=report;print(stage,report['max_part_transfer_bytes'],flush=True)
(A/'pcg-manifest.json').write_text(json.dumps(manifest,indent=2))
