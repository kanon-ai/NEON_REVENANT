"""Original MSX1 challenge art: fixed SCREEN2 tile dictionary and resident sprites.

Every animation phase changes names, never the pattern or color tables. The
independent decoder checks all 8 phases against their intended tile images.
"""
from pathlib import Path
import json, math, re, struct, hashlib
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'assets'; OUT=ROOT.parent/'outputs/msx1'
PALETTE=[(0,0,0),(0,0,0),(33,200,66),(94,220,120),(84,85,237),(125,118,252),
 (212,82,77),(66,235,245),(252,85,84),(255,121,120),(212,193,84),(230,206,128),
 (33,176,59),(201,91,186),(204,204,204),(255,255,255)]

def image(a): return Image.fromarray(np.array(PALETTE,dtype=np.uint8)[np.array(a,dtype=np.uint8)])
def tile(bg=1,fg=7,rows=None):
    rows=rows or [0]*8
    return bytes(rows)+bytes([(fg<<4)|bg])*8
def pixel_tile(p):
    result=bytearray(16)
    for y in range(8):
        colors=sorted(set(p[y])); assert len(colors)<=2
        bg=colors[0];fg=colors[-1]
        result[y]=sum((int(c==fg)<< (7-x)) for x,c in enumerate(p[y]))
        result[y+8]=(fg<<4)|bg
    return bytes(result)
def decode_tile(t):
    return [[(t[8+y]>>4) if t[y]&(128>>x) else t[8+y]&15 for x in range(8)] for y in range(8)]
def decode_screen(vram):
    result=np.zeros((192,256),dtype=np.uint8)
    for y in range(24):
        for x in range(32):
            n=vram[0x3800+y*32+x];o=(y//8)*2048+n*8
            result[y*8:y*8+8,x*8:x*8+8]=decode_tile(vram[o:o+8]+vram[0x2000+o:0x2008+o])
    return result

def world(stage):
    """Tile-authored perspective corridor. Buildings and road lights flow forward.

    The fixed vanishing-point geometry gives every tile a permanent outline;
    interchangeable texture styles move from small far bands to large near
    bands. Unlike scrolling stars, both city walls and the road animate.
    """
    accent=[7,13,8][stage]; secondary=[5,7,13][stage]
    frames=[]
    for phase in range(8):
        tiles=[]
        for ty in range(24):
            row=[]
            for tx in range(32):
                if ty<2 or ty>=22: row.append(tile());continue
                if ty<9:
                    # Jagged luminous skyline; two parallax window belts scroll.
                    height=3+((tx*tx+tx*3+stage*7)%6)
                    building=ty>=9-height
                    if not building:
                        rows=[0]*8
                        if ((tx*19+ty*7+stage*3)%17)==0: rows[3]=0x10
                        row.append(tile(1,secondary,rows));continue
                    edge=tx%3==0
                    if ty==9-height: rows=[0xFF,0x80,0x80,0x80,0x80,0x80,0x80,0x80] if edge else [0xFF]+[0]*7
                    else:
                        shift=(phase+ty+(tx//3))&7
                        rows=[(0x92 if (yy+shift)%4==0 else 0x80 if edge else 0) for yy in range(8)]
                    row.append(tile(4 if tx%3==1 else 1,secondary if ty<6 else accent,rows));continue
                # Perspective splits the moving road and the wall into stable
                # outlines. Stripe speed increases quadratically with depth.
                pixels=np.ones((8,8),dtype=np.uint8)
                for yy in range(8):
                    sy=ty*8+yy; half=12+(sy-72)*1.04
                    left=128-half;right=128+half
                    depth=sy-72
                    band_depth=ty*8-68
                    pulse=((band_depth*band_depth//230-phase*3)%24)<5
                    wallpulse=pulse
                    for xx in range(8):
                        sx=tx*8+xx
                        if sx<left-3 or sx>right+3:
                            # Neon ribbing on walls, including a forward-moving
                            # facade band. Single accent + black per pixel row.
                            rib=((sx+(yy if sx<128 else -yy))&15)==0
                            c=accent if (wallpulse and yy<2) or rib else 1
                        elif sx<left+2 or sx>right-2:
                            c=accent
                        else:
                            lane_distance=abs(sx-128)
                            lane=abs(lane_distance-half/3)<1.3
                            center=lane_distance<1.1
                            # Moving transversal panels keep the road alive even
                            # when the player remains centered and does not fire.
                            c=accent if (pulse and yy<2 and lane_distance<half-6) or (lane and not pulse) or center else 1
                        pixels[yy,xx]=c
                # Shaded road panels use the fixed medium-blue color. Inside
                # a whole road tile, rows with neon have blue + neon; quiet
                # rows use blue/black stipple, never three colors in 8 dots.
                near_half=12+(ty*8-72)*1.04
                if ty>=10 and tx*8>130-near_half and tx*8+7<126+near_half:
                    for yy in range(8):
                        if accent in pixels[yy]:pixels[yy][pixels[yy]==1]=4
                        else:
                            for xx in range(8):
                                if (xx+yy)&1:pixels[yy,xx]=4
                row.append(pixel_tile(pixels))
            tiles.append(row)
        frames.append(tiles)
    # Deduplicate all phases together per 64-line SCREEN2 band. Blank HUD/font
    # tiles reserve 64 entries in the outer bands.
    dictionaries=[]
    for band in range(3):
        d={}
        for f in frames:
            for y in range(band*8,band*8+8):
                if y<2 or y>=22:continue
                for t in f[y]:
                    if t not in d:d[t]=len(d)
        dictionaries.append(d)
    return frames,dictionaries

def build_worlds():
    font=(A/'source/font.bin').read_bytes();reports=[]
    for stage in range(3):
        frames,dictionaries=world(stage)
        counts=list(map(len,dictionaries));print('stage',stage+1,'tiles',counts)
        assert all(n<=limit for n,limit in zip(counts,[192,256,192])),counts
        vram=bytearray(16384)
        for band,d in enumerate(dictionaries):
            for t,n in d.items():
                o=band*2048+n*8;vram[o:o+8]=t[:8];vram[o+8192:o+8200]=t[8:]
            if band!=1:
                o=band*2048+192*8;vram[o:o+512]=font;vram[o+8192:o+8704]=bytes([0xF1])*512
        names=bytearray(); pictures=[]
        for phase,f in enumerate(frames):
            nt=bytes([192 if y<2 or y>=22 else dictionaries[y//8][f[y][x]] for y in range(24) for x in range(32)])
            vram[0x3800:0x3B00]=nt
            pic=decode_screen(vram)
            for y in range(2,22):
                for x in range(32):assert pic[y*8:y*8+8,x*8:x*8+8].tolist()==decode_tile(f[y][x])
            names.extend(nt[64:704]);pictures.append(image(pic))
        vram[0x3800:0x3B00]=bytes([192]*64)+names[:640]+bytes([192]*64)
        (A/f'world-{stage}.bin').write_bytes(vram)
        (A/f'names-{stage}.bin').write_bytes(names)
        pictures[0].resize((768,576),Image.Resampling.NEAREST).save(OUT/f'world-{stage+1}-reference.png')
        pictures[0].save(OUT/f'world-{stage+1}-reference.gif',save_all=True,append_images=pictures[1:],duration=67,loop=0)
        reports.append({'stage':stage+1,'tiles_per_band':counts,'phases':8,'bytes_per_name_update':640,'all_frames_decode_exactly':True,
          'pixel_changes_per_phase':[int(np.count_nonzero(np.array(pictures[i])!=np.array(pictures[(i+1)%8]))) for i in range(8)]})
    return reports

def source_sprites():
    raw=(A/'source/sprite-atlas.bin').read_bytes();meta=json.loads((A/'source/sprite-atlas-manifest.json').read_text())
    assert hashlib.sha256(raw).hexdigest()==meta['sha256']
    pixels=np.empty((len(raw)*2,),dtype=np.uint8);pixels[::2]=np.frombuffer(raw,dtype=np.uint8)>>4;pixels[1::2]=np.frombuffer(raw,dtype=np.uint8)&15
    atlas=Image.fromarray(np.array(meta['palette_rgb8'],dtype=np.uint8)[pixels.reshape(-1,256)])
    groups={};header=(A/'source/sprite-atlas.h').read_text()
    for name in ['player','enemy','explosion','bosses','bullet','pickup','reticle']:
        match=re.search(r'static const Sprite\s+'+name+r'(?:\[\d+\])*\s*=\s*(\{.*?\});',header,re.S)
        values=list(map(int,re.findall(r'\d+',match[1])));groups[name]=[]
        for i in range(0,len(values),4):
            x,y,w,h=values[i:i+4];groups[name].append(atlas.crop((x,y-512,x+w,y-512+h)))
    return groups

def build_sprites():
    sources=source_sprites();patterns=bytearray();records=bytearray();entries={};preview=Image.new('RGB',(512,400),(0,0,0));draw=ImageDraw.Draw(preview);report=[]
    def add(im,name,color,maxw=96,maxh=56,dual=False):
        # Alpha comes from source black. Bright silhouettes retain highlights;
        # global hardware colors replace per-row V9958 colors.
        w=min(im.width,maxw);h=min(im.height,maxh);w=(w+1)//2;h=(h*4+8)//9
        rgb=np.array(im.resize((w,h),Image.Resampling.BOX));lum=rgb.max(axis=2)
        mask=lum>45;bright=(rgb[:,:,1]>120)&(rgb[:,:,2]>110)&(rgb[:,:,0]>100)
        start=len(records);count=0;visual=np.zeros((h*2,w*2),dtype=np.uint8)
        for ty in range((h+15)//16):
            for tx in range((w+15)//16):
                for layer in range(2 if dual else 1):
                    b=bytearray(32); c=(15 if layer else color)
                    for y in range(16):
                        for x in range(16):
                            yy=ty*16+y;xx=tx*16+x
                            if yy<h and xx<w and mask[yy,xx] and (not dual or (bright[yy,xx] if layer else not bright[yy,xx])):
                                b[y+(16 if x>=8 else 0)]|=128>>(x%8);visual[yy*2:yy*2+2,xx*2:xx*2+2]=c
                    if not any(b):continue
                    index=len(patterns)//32;assert index<64
                    patterns.extend(b);records.extend(struct.pack('bbBB',tx*32,ty*32,index*4,c));count+=1
        result=(start,count,w*2,(h*2*9+7)//8)
        col=len(report)%8;row=len(report)//8;preview.paste(image(visual),(col*64,row*62+12));draw.text((col*64,row*62),name,fill='white')
        report.append({'name':name,'pattern_count':count,'width':w*2,'height':h*2});return result
    entries['player']=[add(im,f'P{i}',7,32,24,True) for i,im in enumerate(sources['player'])]
    entries['enemy']=[add(im,f'E{i}',[8,13,11][i//6],48,36) for i,im in enumerate(sources['enemy'])]
    # Explosion sprites share one readable 32-pixel shape per age. The game
    # retains its original effect lifetime; size classes reuse resident art.
    ex=[add(sources['explosion'][age*5+2],f'FX{age}',[15,11,8,13][age],32,32) for age in range(4)]
    entries['explosion']=[ex[age] for age in range(4) for size in range(5)]
    entries['bosses']=[add(im,f'B{i}',[11,13,8][i]) for i,im in enumerate(sources['bosses'])]
    entries['bullet']=[add(sources['bullet'][0],'SHOT',11)]
    entries['pickup']=[add(sources['pickup'][0],'PICK',3)]
    entries['reticle']=[add(sources['reticle'][0],'AIM',7)]
    shapes={'player':(3,),'enemy':(3,6),'explosion':(4,5),'bosses':(3,),'bullet':(),'pickup':(),'reticle':()}
    def init(v,shape):
        if not shape:return '{%d,%d,%d,%d}'%v[0]
        n=math.prod(shape[1:]);return '{'+','.join(init(v[i*n:(i+1)*n],shape[1:]) for i in range(shape[0]))+'}'
    lines=['/* Generated resident TMS9918 mode-1 sprite descriptors. */','#ifndef NEON_ASSETS_H','#define NEON_ASSETS_H','typedef struct { unsigned int offset; unsigned char count,w,h; } Sprite;',f'#define SPRITE_PATTERN_BYTES {len(patterns)}',f'#define SPRITE_DATA_BYTES {len(records)}']
    for name,shape in shapes.items():lines.append('static const Sprite '+name+''.join(f'[{n}]' for n in shape)+' = '+init(entries[name],shape)+';')
    lines.append('#endif');(ROOT/'src/assets.h').write_text('\n'.join(lines)+'\n')
    (A/'sprite-patterns.bin').write_bytes(patterns+bytes(2048-len(patterns)));(A/'sprite-records.bin').write_bytes(records)
    preview.save(OUT/'sprites-reference.png')
    return {'resident_patterns':len(patterns)//32,'pattern_bytes':len(patterns),'records':len(records)//4,'sprites':report}

def build_title():
    font=(A/'source/font.bin').read_bytes();v=bytearray((A/'world-0.bin').read_bytes())
    # Original title glyphs with the native challenge label; all names use the
    # common font dictionary in the outer two bands.
    def text(x,y,s):
        for c in s:v[0x3800+y*32+x]=192+ord(c)-32;x+=1
    v[0x3800:0x3840]=bytes([192])*64;v[0x3AC0:0x3B00]=bytes([192])*64
    text(3,0,'N E O N   R E V E N A N T');text(5,1,'MSX1 CHALLENGE / V1.0')
    text(4,22,'SPACE / JOYSTICK TO START');text(3,23,'CURSOR:MOVE  X:NOVA  ESC:PAUSE')
    (A/'title.bin').write_bytes(v)
    image(decode_screen(v)).resize((768,576),Image.Resampling.NEAREST).save(OUT/'title-reference.png')

def main():
    A.mkdir(exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    worlds=build_worlds();sprites=build_sprites();build_title()
    (A/'manifest.json').write_text(json.dumps({'target':'TMS9918A SCREEN2, 16KiB VRAM','palette_rgb8':PALETTE,'worlds':worlds,'sprite_atlas':sprites,'checks':{'screen2_roundtrip':True,'all_phase_tiles_resident':True,'64_pattern_limit':True}},indent=2)+'\n')
if __name__=='__main__':main()
