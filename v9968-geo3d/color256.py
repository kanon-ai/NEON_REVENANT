"""SCREEN8 resources in unused upper halves of geometry ROM banks."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
from stages import stage_palette
P=Path(__file__).resolve().parent
MATERIALS=[2,3,4,6,7,9,14]

def ramp(base):
    return [tuple(round(min(255,c*(.52+shade*.065))) for c in base[k]) for k in MATERIALS for shade in range(16)]

def enhance(banks,base):
    src=Image.open(P/'assets/material-atlas-v1.png').convert('RGB');w,h=src.size
    tiles=[src.crop(box) for box in [(0,0,w//2,h//2),(w//2,0,w,h//2),(0,h//2,w//2,h),(w//2,h//2,w,h)]]
    extra=src.resize((256,256)).quantize(colors=96,method=Image.Quantize.MEDIANCUT).getpalette()[:288]
    extra=[tuple(extra[i:i+3]) for i in range(0,384,3)]
    extra=[c for c in extra if len(c)==3]
    # Dedicated, stage-invariant dawn ramp; no noisy image overlay or dithering.
    dawn=[tuple(round(a+(b-a)*i/31) for a,b in zip((12,22,48),(163,104,93))) for i in range(32)]
    extra+=dawn
    colors=base+ramp(base)+extra
    pal=Image.new('P',(1,1));pal.putpalette(sum(map(list,colors),[]))
    def quant(im):return im.quantize(palette=pal,dither=Image.Dither.NONE)
    def unpack(ids):
        a=np.frombuffer(b''.join(bytes(banks[i]) for i in ids),dtype=np.uint8)
        z=np.empty(a.size*2,dtype=np.uint8);z[::2]=a>>4;z[1::2]=a&15
        im=Image.fromarray(z.reshape(-1,256));im=im.convert('P');im.putpalette(pal.getpalette());return im
    resources=[]
    for stage in range(5):
        old=unpack([4,5] if stage==0 else [240+(stage-1)*2,241+(stage-1)*2])
        rgb=tiles[0].resize((256,130),Image.Resampling.LANCZOS)
        a=np.asarray(rgb).astype(float)
        fade=np.linspace(1,.3,130)[:,None,None];a=a*fade
        if stage==4:
            top=np.array([25,30,62]);bottom=np.array([188,113,87]);t=np.linspace(0,1,130)[:,None,None]
            a=top*(1-t)+bottom*t+np.asarray(rgb)*.1
            a=np.broadcast_to(a,(130,256,3)).copy()
        im=Image.new('P',(256,256),1);im.putpalette(pal.getpalette())
        if stage!=3:im.paste(quant(Image.fromarray(np.uint8(np.clip(a,0,255)))),(0,0))
        im.paste(old.crop((0,130,256,256)),(0,130))
        if stage==4:
            # Direct indices avoid remapping the sky through the stage's material palette.
            d=ImageDraw.Draw(im)
            for y in range(130):d.line((0,y,255,y),fill=224+round(y*31/129))
        resources.append(im.tobytes());im.save(P/f'out/sky256-{stage}.png')
    hud=unpack([6,7]);resources.append(hud.tobytes())
    tex=Image.new('P',(256,128),2);tex.putpalette(pal.getpalette())
    for tile,box in [(1,(0,0,64,128)),(1,(64,0,128,128)),(3,(128,0,192,64)),(3,(192,0,256,64)),(2,(128,64,192,128)),(2,(192,64,256,128))]:
        x,y,xx,yy=box;tex.paste(quant(tiles[tile].resize((xx-x,yy-y),Image.Resampling.LANCZOS)),(x,y))
    # Area-specific armor liveries, sharing the existing palette and atlas.
    from battleship_art import sector_texture
    for theme in range(4):
        x=128+(theme&1)*32;y=(theme>>1)*32
        tile=sector_texture(theme,pal.getpalette())
        tex.paste(tile,(x,y))
    from battleship_art import deck_texture
    final_deck=deck_texture(pal.getpalette());tex.paste(final_deck,(192,0))
    final_deck.save(P/'out/final-boss-deck.png')
    # Stationary industrial fan: same octagonal rim and four blades, one quad.
    import math
    fan=Image.new('P',(64,64),2);fan.putpalette(pal.getpalette());fd=ImageDraw.Draw(fan)
    def ring(a,r):return (31.5+31.5*math.cos(a)*r/88,31.5-31.5*math.sin(a)*r/88)
    fd.polygon([ring(math.tau*i/8,88) for i in range(8)],fill=14)
    fd.polygon([ring(math.tau*i/8,64) for i in range(8)],fill=2)
    for i in range(4):
        a=math.tau*i/4+.3
        fd.polygon([ring(ang,r) for ang,r in [(a,12),(a+.18,62),(a+.65,54),(a+.9,12)]],fill=7)
    tex.paste(fan,(192,64))
    resources.append(tex.tobytes());tex.save(P/'out/texture-atlas256.png')
    title=unpack([248,249]);rgb=Image.open(P/'assets/title-reference.png').convert('RGB').crop((32,16,288,228));im=quant(rgb)
    # Keep all existing wording and controls; restore full-color original art.
    for box in [(0,0,256,15),(43,86,213,154),(33,181,224,192),(0,196,256,212)]:im.paste(title.crop(box),box[:2])
    title.paste(im,(0,0));resources.append(title.tobytes());title.save(P/'out/title256.png')
    resources.append(unpack([237,238]).crop((0,0,256,160)).tobytes())
    palette=bytearray()
    for stage in range(5):
        b=stage_palette(stage,base)
        for rgb in b+ramp(b)+extra:palette.extend(round(c/255*31) for c in rgb)
    banks[239]=palette+bytearray(16384-len(palette))
    slots=iter(list(range(8,40))+list(range(101,229)));allocation=[]
    for resource,data in enumerate(resources):
        descriptor=[]
        for offset in range(0,len(data),8192):
            bank=next(slots)
            assert not any(banks[bank][8190:16382]),bank
            banks[bank][8190:16382]=data[offset:offset+8192].ljust(8192,b'\0')
            descriptor.append(bank)
        assert len(descriptor)<=8
        banks[239][4096+resource*8:4096+resource*8+len(descriptor)]=bytes(descriptor)
        allocation.append(descriptor)
    # Exact positive magnitude of pixel * depth / 170, shared for X and Y.
    table_banks=[]
    for group in range(18):
        bank=next(slots);assert not any(banks[bank][8190:16382]),bank
        raw=np.array([[pixel*(group*16+row)*5//170 for pixel in range(256)] for row in range(16)],dtype='<i2').tobytes()
        banks[bank][8190:16382]=raw;table_banks.append(bank)
    banks[239][4200:4218]=bytes(table_banks)
    (P/'out/color256.json').write_text(json.dumps({'palette_entries':len(colors),'resource_banks':allocation,'projection_banks':table_banks,'framebuffer_rows':[[0,211],[256,467]],'assets_rows':[512,1023]},indent=2))
    return colors
