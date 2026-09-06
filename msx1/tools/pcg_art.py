"""Original-world PCG art for a 16KB-VRAM first-generation MSX.

Public API: generate_frames(stage, source_dir, quality='high') returns
uint8 color indices with shape (16, 192, 256). stage is 1, 2 or 3.
source_dir contains palette.json and world/stage-{1,2,3}.bin, the original
NEON REVENANT V9990 art. No Pillow resizing or renderer runs on the Z80.

The default preserves 128x80 geometry with 2x2 sampling, represents opaque
shadows as fixed blue/purple/red pixel dither, and approximates tiles using
shared original tile shapes. Every 8-pixel row has at most two TMS colors.
Outer 64-line bands use at most 96 PCGs per frame; middle uses at most 128.
HUD y0..15 and y176..191 is black and is never used as world art.

Quality 'fast' uses 256 shared shapes per band; 'high' uses 512. These are
offline dictionaries across 16 phases, not simultaneous VRAM requirements.
'coarse' is a comparison at 64x40 with no dictionary approximation.
"""
from pathlib import Path
import numpy as np
from PIL import Image

PALETTE = [(0,0,0),(0,0,0),(33,200,66),(94,220,120),(84,85,237),(125,118,252),
           (212,82,77),(66,235,245),(252,85,84),(255,121,120),(212,193,84),(230,206,128),
           (33,176,59),(201,91,186),(204,204,204),(255,255,255)]
LIMITS = (96,128,96)
WEIGHTS = np.tile(np.array([2,3,1], dtype=np.float64),16)

def _two_colors(indices):
    rows=indices.reshape(-1,8).copy()
    pal=np.array(PALETTE,dtype=np.int64)
    dist=np.sum((pal[:,None]-pal[None,:])**2*np.array([2,3,1]),axis=2)
    for i,line in enumerate(rows):
        colors,counts=np.unique(line,return_counts=True)
        if len(colors)<=2:continue
        order=np.lexsort((colors,-counts))[:2]
        a,b=colors[order]
        rows[i]=np.where(dist[line,a]<=dist[line,b],a,b)
    return rows.reshape(indices.shape)

def _source_frames(stage,source_dir,step):
    if stage not in (1,2,3):raise ValueError('stage must be 1, 2 or 3')
    raw=np.frombuffer((Path(source_dir)/'world'/f'stage-{stage}.bin').read_bytes(),dtype=np.uint8)
    if len(raw)!=16*256*180//2:raise ValueError('Expected 16 original 256x180 4bpp frames')
    source=np.empty(raw.size*2,dtype=np.uint8)
    source[::2]=raw>>4;source[1::2]=raw&15
    source=source.reshape(16,180,256)
    basic=np.array([1,1,4,5,7,7,7,15,4,5,13,9,6,8,10,11],dtype=np.uint8)
    yy,xx=np.indices((160,256))
    bayer=np.array([[0,2],[3,1]])[yy%2,xx%2]
    output=np.ones((16,192,256),dtype=np.uint8)
    for phase,frame in enumerate(source):
        small=np.array(Image.fromarray(frame).resize((256//step,160//step),Image.Resampling.NEAREST))
        original=np.repeat(np.repeat(small,step,axis=0),step,axis=1)
        full=basic[original]
        # Surface coverage gives four apparent blue intensities without
        # changing the TMS palette. Dither stays stationary on screen.
        for material,color,level in [(2,4,1),(3,4,2),(8,13,1),(9,5,2),(12,8,1)]:
            mask=original==material
            full[mask]=np.where(bayer[mask]<level,color,1)
        full[original==4]=4
        output[phase,16:176]=full
    return _two_colors(output)

def _patches(frames,band):
    start=max(16,band*64);end=min(176,band*64+64)
    return frames[:,start:end].reshape(16,(end-start)//8,8,32,8).transpose(0,1,3,2,4).reshape(16,-1,64)

def _features(p):
    rgb=np.array(PALETTE,dtype=np.float64)[p.reshape(-1,8,8)]
    # Integer-valued 2x2 light sums. Float64 operations below remain exact
    # integers within their range, making medoid tie-breaking stable.
    return rgb.reshape(-1,4,2,4,2,3).sum(axis=(2,4)).reshape(len(p),-1)

def _distances(a,b):
    return np.maximum(0,(a*a*WEIGHTS).sum(1)[:,None]+(b*b*WEIGHTS).sum(1)[None,:]-2*(a*WEIGHTS)@b.T)

def _medoids(values,counts,k,rounds=5):
    k=min(k,len(values));chosen=[int(np.argmax(counts))]
    closest=_distances(values,values[chosen]).ravel()
    # Python integer scores avoid floating square-root or large-product
    # rounding in the weighted farthest-point initialization.
    for _ in range(k-1):
        scores=[int(d)*int(d)*int(c) for d,c in zip(closest,counts)]
        chosen.append(max(range(len(scores)),key=scores.__getitem__))
        closest=np.minimum(closest,_distances(values,values[chosen[-1]:chosen[-1]+1]).ravel())
    center=values[chosen]
    for _ in range(rounds):
        nearest=_distances(values,center).argmin(1)
        for j in range(k):
            members=np.flatnonzero(nearest==j)
            if len(members):
                weights=counts[members]
                total=(values[members]*weights[:,None]).sum(0)
                cost=(values[members]**2*WEIGHTS).sum(1)*weights.sum()-2*(values[members]*WEIGHTS)@total
                chosen[j]=int(members[np.argmin(cost)])
        center=values[chosen]
    return np.array(sorted(set(chosen)))

def _approximate(frames,codebook):
    output=frames.copy()
    for band in range(3):
        p=_patches(frames,band)
        unique,inverse,counts=np.unique(p.reshape(-1,64),axis=0,return_inverse=True,return_counts=True)
        f=_features(unique)
        selected=_medoids(f,counts,codebook)
        d=_distances(f,f[selected])
        indices=d.argmin(1)[inverse].reshape(p.shape[:2])
        for phase in range(16):
            used,qty=np.unique(indices[phase],return_counts=True)
            if len(used)>LIMITS[band]:
                keep=_medoids(f[selected[used]],qty,LIMITS[band],rounds=3)
                active=used[keep]
                src=inverse.reshape(p.shape[:2])[phase]
                indices[phase]=active[d[src][:,active].argmin(1)]
        rebuilt=unique[selected[indices]].reshape(16,p.shape[1]//32,32,8,8).transpose(0,1,3,2,4)
        start=max(16,band*64);end=min(176,band*64+64)
        output[:,start:end]=rebuilt.reshape(16,end-start,256)
    return output

def generate_frames(stage,source_dir,quality='high'):
    """Return sixteen legal, deterministic, indexed SCREEN2 world frames."""
    if quality not in ('high','fast','coarse'):raise ValueError('quality must be high, fast or coarse')
    frames=_source_frames(stage,source_dir,4 if quality=='coarse' else 2)
    if quality!='coarse':frames=_approximate(frames,512 if quality=='high' else 256)
    assert frames.shape==(16,192,256) and frames.dtype==np.uint8
    assert np.all(frames[:,:16]==1) and np.all(frames[:,176:]==1)
    for band in range(3):
        for patches in _patches(frames,band):
            assert len(np.unique(patches,axis=0))<=LIMITS[band]
    return frames
