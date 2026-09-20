"""Deterministic V9938 SCREEN4 hardware-sprite conversion for NEON REVENANT.

The copied source atlas is read locally; no V9990 hardware/runtime is used.
Every 50-byte record contains signed screen dx/dy, 32 pattern bytes, and
16 per-row colors. 16x16 patterns are displayed with global MAG=2.
"""
from pathlib import Path
from itertools import combinations
import hashlib
import json
import math
import re
import shutil
import struct

from PIL import Image, ImageDraw
from art_palette import PALETTE_RGB3, PALETTE

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'
SOURCE=ASSETS/'source'
RECORD_BYTES=50
LAYERS={'player':2,'enemy':1,'explosion':1,'bosses':2,'bullet':1,'pickup':1,'reticle':1}
SHAPES={'player':(3,),'enemy':(3,6),'explosion':(4,5),'bosses':(3,),'bullet':(),'pickup':(),'reticle':()}


def copy_sources_once():
    SOURCE.mkdir(parents=True,exist_ok=True)
    files=[('sprite-atlas.bin',ROOT.parent/'assets/vram.bin'),
           ('sprite-atlas.h',ROOT.parent/'src/assets.h'),
           ('sprite-atlas-manifest.json',ROOT.parent/'assets/manifest.json')]
    for name,original in files:
        target=SOURCE/name
        if not target.exists():
            if not original.is_file():
                raise FileNotFoundError('Missing copied sprite source: '+str(target))
            shutil.copyfile(original,target)


def read_sources():
    raw=(SOURCE/'sprite-atlas.bin').read_bytes()
    manifest=json.loads((SOURCE/'sprite-atlas-manifest.json').read_text(encoding='utf-8'))
    assert len(raw)==manifest['bytes']
    assert hashlib.sha256(raw).hexdigest()==manifest['sha256']
    palette=manifest['palette_rgb8']
    pixels=bytes(c for byte in raw for index in (byte>>4,byte&15) for c in palette[index])
    atlas=Image.frombytes('RGB',(256,len(raw)//128),pixels)
    header=(SOURCE/'sprite-atlas.h').read_text(encoding='ascii')
    groups={}
    for name,shape in SHAPES.items():
        match=re.search(r'static const Sprite\s+'+name+r'(?:\[\d+\])*\s*=\s*(\{.*?\});',header,re.S)
        assert match,name
        values=list(map(int,re.findall(r'\d+',match[1])))
        assert len(values)%4==0
        rects=[tuple(values[i:i+4]) for i in range(0,len(values),4)]
        assert len(rects)==(math.prod(shape) if shape else 1)
        groups[name]=[]
        for x,y,w,h in rects:
            image=atlas.crop((x,y-512,x+w,y-512+h))
            groups[name].append((image,(x,y,w,h)))
    return groups


def luminance(rgb):
    return (.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2])/255


def downsample(source,kind):
    width=(source.width+1)//2
    height=(source.height*4+8)//9
    rgba=source.convert('RGBA')
    # A one-plane enemy has no opaque dark second color. Convert only the
    # source's deep internal shadows to true cutouts, retaining bright armor,
    # wings, weapon barrels and the warm core rather than a solid rectangle.
    shadow_cutoff=.23 if source.width>=18 else .14
    rgba.putalpha(Image.frombytes('L',source.size,bytes(0 if p==(0,0,0) or
        (kind=='enemy' and luminance(p)<shadow_cutoff) else 255
        for p in zip(*[iter(source.tobytes())]*3))))
    small=rgba.resize((width,height),Image.Resampling.BOX)
    result=[]
    for y in range(height):
        row=[]
        for x in range(width):
            r,g,b,a=small.getpixel((x,y))
            # Thin reticle edges survive, while mostly-empty corner samples stay clear.
            row.append((r,g,b) if a>=72 else None)
        result.append(row)
    return result


def color_distance(a,b):
    # Slightly favor luma/detail over blue hue errors on RGB3's coarse grid.
    return (a[0]-b[0])**2*.85+(a[1]-b[1])**2*1.1+(a[2]-b[2])**2


def best_pair(pixels):
    visible=[p for p in pixels if p is not None]
    if not visible:
        return (0,0),[None]*len(pixels)
    weights=[1+2*luminance(p) for p in visible]
    distances=[[color_distance(p,PALETTE[c])*weights[i] for c in range(1,16)]
               for i,p in enumerate(visible)]
    pair=min(combinations(range(1,16),2),key=lambda pair:
        sum(min(d[pair[0]-1],d[pair[1]-1]) for d in distances))
    # Stable dark-first assignment makes the secondary plane an illuminated surface.
    pair=tuple(sorted(pair,key=lambda c:(luminance(PALETTE[c]),c)))
    assignments=[None if p is None else min(range(2),key=lambda layer:
        color_distance(p,PALETTE[pair[layer]])) for p in pixels]
    return pair,assignments


def best_single(pixels,kind):
    visible=[p for p in pixels if p is not None]
    if not visible:
        return (0,),[None]*len(pixels)
    # A single hardware color cannot preserve horizontal material changes.
    # Keep the silhouette and prioritize lit copper/amber threat surfaces or
    # cyan item/reticle light; neutral rows retain the visible armor average.
    if kind in ('enemy','explosion','bullet'):
        accents=[p for p in visible if p[0]>p[1]*1.35 and p[0]>95]
    elif kind in ('pickup','reticle'):
        accents=[p for p in visible if p[1]>p[0]*1.2 and p[1]>90]
    else:
        accents=[]
    selected=accents or sorted(visible,key=luminance,reverse=True)[:max(1,(len(visible)+1)//2)]
    weights=[.5+2*luminance(p) for p in selected]
    target=tuple(sum(p[c]*w for p,w in zip(selected,weights))/sum(weights) for c in range(3))
    color=min(range(1,16),key=lambda c:color_distance(target,PALETTE[c]))
    return (color,),[None if p is None else 0 for p in pixels]


def convert(source,kind):
    small=downsample(source,kind)
    width,height=len(small[0]),len(small)
    expected=[[None]*width for _ in range(height)]
    records=[]
    for tile_y in range((height+15)//16):
        for tile_x in range((width+15)//16):
            patterns=[bytearray(32) for _ in range(LAYERS[kind])]
            colors=[bytearray(16) for _ in range(LAYERS[kind])]
            for row in range(16):
                y=tile_y*16+row
                pixels=[small[y][x] if y<height and x<width else None
                        for x in range(tile_x*16,tile_x*16+16)]
                palette,assignments=best_pair(pixels) if LAYERS[kind]==2 else best_single(pixels,kind)
                for layer,color in enumerate(palette):
                    colors[layer][row]=color
                for column,layer in enumerate(assignments):
                    if layer is None:
                        continue
                    x=tile_x*16+column
                    expected[y][x]=palette[layer]
                    offset=row+(16 if column>=8 else 0)
                    patterns[layer][offset]|=1<<(7-column%8)
            for pattern,color in zip(patterns,colors):
                if any(pattern):
                    records.append(struct.pack('bb',tile_x*32,tile_y*32)+pattern+color)
    assert all(len(record)==RECORD_BYTES for record in records)
    # Independently decode the actual record byte order and MAG2 placement.
    decoded=decode(records,width*2,height*2)
    target=Image.new('RGB',(width,height),(0,0,0))
    target.putdata([PALETTE[c] if c is not None else (0,0,0) for row in expected for c in row])
    target=target.resize((width*2,height*2),Image.Resampling.NEAREST)
    assert decoded.tobytes()==target.tobytes()
    assert sum(p is not None for row in small for p in row)==sum(c is not None for row in expected for c in row)
    return records,decoded,small


def decode(records,width,height):
    image=Image.new('RGB',(width,height),(0,0,0))
    occupied=set()
    for record in records:
        dx,dy=struct.unpack('bb',record[:2])
        for y in range(16):
            color=record[34+y]
            assert 0<=color<16
            bits=(record[2+y]<<8)|record[18+y]
            if bits:
                assert color!=0
            for x in range(16):
                if not bits&(1<<(15-x)):
                    continue
                for yy in range(dy+y*2,dy+y*2+2):
                    for xx in range(dx+x*2,dx+x*2+2):
                        assert 0<=xx<width and 0<=yy<height
                        assert (xx,yy) not in occupied,'Two color planes overlap'
                        occupied.add((xx,yy))
                        image.putpixel((xx,yy),PALETTE[color])
    return image


def initializer(entries,shape):
    if not shape:
        return '{%d,%d,%d,%d,%d}'%entries[0]
    if len(shape)==1:
        return '{'+','.join('{%d,%d,%d,%d,%d}'%v for v in entries)+'}'
    stride=math.prod(shape[1:])
    return '{\n '+',\n '.join(initializer(entries[i:i+stride],shape[1:])
        for i in range(0,len(entries),stride))+'\n}'


def main():
    ASSETS.mkdir(parents=True,exist_ok=True)
    (ROOT/'src').mkdir(exist_ok=True)
    copy_sources_once()
    sources=read_sources()
    blob=bytearray()
    groups={}
    manifest={'format':'SCREEN4 sprite mode 2;16x16;MAG2','record_bytes':50,
        'record_layout':'signed dx,dy;16 left pattern rows;16 right pattern rows;16 colors',
        'palette_rgb3':PALETTE_RGB3,'sprites':{},'checks':{
            'hardware_record_round_trip':True,'disjoint_color_planes':True,
            'visible_mask_preserved':True,'enemy_deep_shadow_cutouts':True,
            'source_alpha_preserved_for_two_plane_art':True}}
    previews={}
    for name,shape in SHAPES.items():
        entries=[]
        for index,(source,rect) in enumerate(sources[name]):
            records,decoded,small=convert(source,name)
            offset=len(blob)
            blob.extend(b''.join(records))
            entries.append((offset,len(records),source.width,source.height,offset//50))
            label=f'{name}_{index}'
            previews[label]=decoded
            scanline_count=max(sum(record[1]<=y<record[1]+32 for record in records)
                for y in range(decoded.height)) if records else 0
            manifest['sprites'][label]={'offset':offset,'count':len(records),'w':source.width,'h':source.height,
                'pattern_width':len(small[0]),'pattern_height':len(small),'display_width':decoded.width,
                'display_height':decoded.height,'max_record_slots_per_scanline':scanline_count,
                'source_rect':rect}
        groups[name]=entries
    assert len(blob)<=32768
    (ASSETS/'sprites.bin').write_bytes(blob)
    header=['/* Generated SCREEN4 hardware-sprite descriptors. */','#ifndef NEON_ASSETS_H','#define NEON_ASSETS_H',
        'typedef struct { unsigned int offset; unsigned char count,w,h,first; } Sprite;',
        '#define SPRITE_RECORD_BYTES 50','#define SPRITE_DATA_BYTES '+str(len(blob))]
    for name,shape in SHAPES.items():
        suffix=''.join(f'[{n}]' for n in shape)
        header.append('static const Sprite '+name+suffix+' = '+initializer(groups[name],shape)+';')
    # Exactly the former signed C expression, evaluated offline for the
    # complete visible coordinate range (including negative clipped origins).
    yy=[16+int((y-18)*8/9) for y in range(-32,224)]
    header.append('static const signed int video_y_table[256] = {'+','.join(map(str,yy))+'};')
    header+=['#endif','']
    (ROOT/'src/assets.h').write_text('\n'.join(header),encoding='ascii')
    # Native display dimensions appear beside nearest-neighbor magnifications.
    sheet=Image.new('RGB',(960,680),PALETTE[1])
    d=ImageDraw.Draw(sheet)
    d.text((14,8),'NEON REVENANT / MSX2 EDITION / SCREEN4 HARDWARE SPRITES',fill=PALETTE[7])
    d.text((14,24),'Native MAG2 raster and enlarged pixel detail. Counts are hardware sprite records.',fill=PALETTE[6])
    for column in range(3):
        x=14+column*320
        for group,y,index in [('player',58,column),('enemy',224,column*6+5),('bosses',426,column)]:
            label=f'{group}_{index}'
            sprite=previews[label]
            count=manifest['sprites'][label]['count']
            d.text((x,y),f'{label.upper()}  {count} RECORDS',fill=PALETTE[7] if group!='enemy' else PALETTE[14])
            sheet.paste(sprite,(x,y+20))
            scale=3 if group!='bosses' else 2
            sheet.paste(sprite.resize((sprite.width*scale,sprite.height*scale),Image.Resampling.NEAREST),(x,y+80))
    sheet.save(ASSETS/'sprites-preview.png')
    # Every small enemy and explosion frame remains inspectable at actual size.
    detail=Image.new('RGB',(640,440),PALETTE[1])
    dd=ImageDraw.Draw(detail)
    for kind in range(3):
        x=8
        for step in range(6):
            label=f'enemy_{kind*6+step}'
            spr=previews[label]
            dd.text((x,kind*65),str(manifest['sprites'][label]['count']),fill=PALETTE[7])
            detail.paste(spr,(x,kind*65+15));x+=spr.width+18
    for phase in range(4):
        x=8
        for step in range(5):
            spr=previews[f'explosion_{phase*5+step}']
            detail.paste(spr,(x,206+phase*57));x+=spr.width+13
    for i,name in enumerate(['bullet','pickup','reticle']):
        detail.paste(previews[name+'_0'],(480+i*45,220))
    detail.save(ASSETS/'sprite-scales-native.png')
    detail.resize((1280,880),Image.Resampling.NEAREST).save(ASSETS/'sprite-scales-preview.png')
    manifest.update({'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [SOURCE/'sprite-atlas.bin',SOURCE/'sprite-atlas.h',SOURCE/'sprite-atlas-manifest.json']}})
    (ASSETS/'sprites-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'bytes':len(blob),'records':len(blob)//50,'actors':len(previews),
        'player_counts':[v[1] for v in groups['player']],'boss_counts':[v[1] for v in groups['bosses']],
        'sha256':manifest['sha256']},indent=2))


if __name__=='__main__':
    main()
