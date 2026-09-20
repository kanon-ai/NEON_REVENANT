"""Original deterministic modular battleship art for the V9990 feature lab.

The 256x64 4bpp atlas occupies VRAM 0x7E000..0x7FFFF. Its final four rows
(512 bytes at 0x7FE00) are zero and reserved for the hardware cursors.
Only this feature atlas/header/preview are generated; original art is read
only through the shared 16-colour art_palette module. Index zero is clear.
"""
from pathlib import Path
import hashlib
import json
import math

import numpy as np
from PIL import Image, ImageDraw

from art_palette import PALETTE, PALETTE_RGB5

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets'
BASE_Y = 4032
PLACEMENT = {
    'hull': (0, 0, 176, 60),
    'arm_left': (176, 0, 24, 60),
    'arm_right': (200, 0, 24, 60),
    'core_0': (224, 0, 30, 30),
    'core_1': (224, 30, 30, 30),
}


def hull():
    im = Image.new('L', (176, 60), 0)
    d = ImageDraw.Draw(im)
    # A broad, continuous stealth silhouette, with a raised command bridge
    # and two swept wings. Every edge remains inside a transparent margin.
    shell = [(1,32),(24,26),(42,19),(63,16),(73,8),(82,3),(94,3),
             (104,9),(112,16),(132,20),(152,27),(174,33),(172,40),
             (149,44),(137,50),(121,53),(113,58),(62,58),(55,54),
             (38,50),(25,44),(3,40)]
    d.polygon(shell, fill=1, outline=3)
    d.polygon([(5,32),(44,20),(64,19),(75,12),(101,12),(114,19),
               (132,23),(170,33),(158,37),(116,31),(62,30),(18,38)], fill=2)
    d.line([(6,32),(45,21),(64,19),(76,12)], fill=4)
    d.line([(101,12),(114,19),(132,23),(169,33)], fill=9)
    # Long bevelled wing armour, repeated vent ridges and low warm lights.
    for right in (False, True):
        def points(vertices):
            return [(175-x if right else x, y) for x, y in vertices]
        d.polygon(points([(7,34),(43,24),(65,22),(57,33),(33,41),(7,39)]), fill=3)
        d.polygon(points([(8,37),(35,33),(58,25),(54,33),(30,42),(8,40)]), fill=2)
        d.line(points([(12,34),(44,25),(60,24)]), fill=9)
        d.line(points([(10,39),(32,41),(54,34)]), fill=1)
        d.polygon(points([(27,31),(43,27),(53,26),(48,30),(33,35)]), fill=1)
        for i in range(5):
            x = 32 + i * 3
            d.line(points([(x,31-i//2),(x+1,33-i//2)]), fill=4)
        d.polygon(points([(27,41),(49,34),(58,35),(53,45),(40,49)]), fill=8)
        d.line(points([(29,41),(48,35),(56,35)]), fill=10)
        d.polygon(points([(40,39),(49,36),(51,40),(45,45),(39,46)]), fill=2)
        d.line(points([(40,39),(48,37)]), fill=9)
        # A tiny seam light is brighter than its socket, not a bright outline
        # surrounding the whole enemy in the player's cyan colour.
        for x in (15,19,23):
            d.line(points([(x,36),(x,37)]), fill=11)
        d.polygon(points([(57,46),(67,47),(67,54),(62,56),(54,52)]), fill=3)
        d.line(points([(58,47),(65,48),(64,53)]), fill=9)
        for x in (57,60,63):
            d.line(points([(x,52),(x+1,53)]), fill=5)
    # The command bridge rises out of the horizontal wings in three facets.
    d.polygon([(69,20),(76,10),(82,6),(94,6),(101,11),(108,20),
               (101,24),(75,24)], fill=3, outline=1)
    d.polygon([(76,10),(83,7),(94,7),(100,11),(101,17),(75,17)], fill=9)
    d.polygon([(78,11),(98,11),(100,16),(76,16)], fill=1)
    d.line((79,12,96,12), fill=4)
    for x, color in ((78,5),(82,6),(86,6),(90,5),(94,5)):
        d.rectangle((x,14,x+2,15), fill=color)
    d.line((73,20,104,20), fill=4)
    d.line((76,22,100,22), fill=2)
    d.line((87,2,87,6), fill=9)
    d.point((87,1), fill=11)
    # Side mounts and narrow slotted shutters make the wing/hatch depth read.
    for x in (52,116):
        d.polygon([(x,25),(x+8,23),(x+12,26),(x+11,34),(x+4,37),(x,32)], fill=1)
        d.polygon([(x+2,26),(x+8,25),(x+10,27),(x+8,31),(x+3,32)], fill=9)
        d.rectangle((x+3,28,x+7,29), fill=2)
        d.line((x+3,30,x+7,30), fill=11)
        d.line((x+3,34,x+7,33), fill=4)
    # Central armoured reactor recess. The two animated core tiles overlay
    # at (73,24); the recess is opaque and never reveals scenery through it.
    d.polygon([(76,23),(99,23),(110,34),(110,47),(100,57),
               (75,57),(65,47),(65,34)], fill=1, outline=4)
    d.polygon([(77,25),(98,25),(106,34),(107,46),(99,54),
               (76,54),(68,46),(68,35)], fill=8, outline=9)
    d.line([(78,26),(98,26),(104,32)], fill=10)
    d.line([(70,46),(77,52),(98,52),(105,46)], fill=3)
    d.rectangle((72,32,103,47), fill=1)
    # Emitter sockets on either side of the central shell.
    for x in (63,109):
        d.line((x,35,x,43), fill=1, width=2)
        d.line((x,36,x,38), fill=13)
        d.point((x,39), fill=15)
    # Cleanly bordered lateral attachment joints remain covered when the
    # independently blitted arms recoil a few pixels vertically.
    for x in (2,168):
        d.rectangle((x,31,x+4,37), fill=1)
        d.line((x+1,31,x+1,36), fill=9)
        d.line((x+3,32,x+3,36), fill=4)
    return im


def arm(right=False):
    im = Image.new('L', (24,60), 0)
    d = ImageDraw.Draw(im)
    # Curved mechanical shoulder, narrow neck, and a forward cannon with
    # an elliptical muzzle. Its angular outside avoids a rectangular slab.
    d.polygon([(14,3),(20,6),(22,17),(22,31),(18,37),(18,45),
               (21,50),(19,56),(14,58),(5,57),(1,52),(2,44),
               (5,38),(6,27),(8,16),(10,9)], fill=1, outline=3)
    d.polygon([(15,5),(19,8),(20,19),(19,29),(15,34),(11,31),
               (11,21),(12,12)], fill=9)
    d.polygon([(12,11),(14,8),(14,24),(11,31),(8,28),(9,19)], fill=3)
    d.line([(16,8),(18,10),(19,20)], fill=6)
    d.polygon([(11,22),(17,22),(18,29),(13,34),(7,34),(8,29)], fill=8)
    d.line([(10,26),(15,25),(15,29),(10,31)], fill=10)
    d.rectangle((17,25,21,32), fill=2)
    d.line((18,26,20,26), fill=4)
    d.line((18,30,20,30), fill=9)
    d.polygon([(7,34),(14,33),(16,38),(15,46),(5,46),(4,42)], fill=3)
    d.line([(8,35),(12,35),(13,40)], fill=9)
    d.polygon([(8,36),(10,36),(10,42),(7,44),(6,42)], fill=1)
    d.line((11,39,11,44), fill=5)
    d.polygon([(5,42),(15,41),(19,47),(19,53),(14,57),
               (6,56),(2,52),(2,47)], fill=8, outline=9)
    d.ellipse((4,44,17,55), fill=1, outline=10)
    d.arc((4,44,17,55), 185,340, fill=11, width=2)
    d.ellipse((7,47,14,53), fill=12, outline=13)
    d.ellipse((9,48,13,51), fill=14)
    d.point((11,49), fill=15)
    for y in (35,38,41):
        d.line((3,y+4,4,y+5), fill=4)
    if right:
        im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return im


def core(phase):
    im = Image.new('L',(30,30),0)
    d = ImageDraw.Draw(im)
    # Two ten-bladed rotor phases. Opaque backing gives the root renderer
    # a solid moving assembly; clear corners preserve the hatch silhouette.
    d.polygon([(9,2),(20,2),(27,9),(27,20),(20,27),(9,27),
               (2,20),(2,9)], fill=1, outline=10)
    d.ellipse((4,4,25,25), fill=8, outline=3)
    angle = math.pi/10*phase
    for i in range(10):
        a = math.tau*i/10+angle
        b = a+math.pi/7
        vertices = [(15+round(math.cos(a)*11),15+round(math.sin(a)*11)),
                    (15+round(math.cos(b)*11),15+round(math.sin(b)*11)),
                    (15+round(math.cos(b+.13)*7),15+round(math.sin(b+.13)*7)),
                    (15+round(math.cos(a+.13)*8),15+round(math.sin(a+.13)*8))]
        d.polygon(vertices,fill=13 if i%2 else 11)
    d.ellipse((8,8,21,21), fill=12, outline=14)
    d.ellipse((10,10,19,19), fill=14 if phase else 13)
    d.polygon([(14,10),(18,13),(18,16),(15,19),(11,16),(11,13)], fill=15)
    d.line((13,12,16,12), fill=7)
    d.point((13,13), fill=7)
    for x,y in ((14,3),(25,14),(14,25),(3,14)):
        d.point((x,y),fill=11 if phase else 14)
    return im


def rgba(indexed):
    a=np.array(indexed,dtype=np.uint8)
    rgb=np.array(PALETTE,dtype=np.uint8)[a]
    alpha=np.where(a==0,0,255).astype(np.uint8)
    return Image.fromarray(np.dstack((rgb,alpha)))


def build():
    pieces={'hull':hull(),'arm_left':arm(),'arm_right':arm(True),
            'core_0':core(0),'core_1':core(1)}
    atlas=Image.new('L',(256,64),0)
    occupied=np.zeros((64,256),dtype=np.uint8)
    for name,im in pieces.items():
        x,y,w,h=PLACEMENT[name]
        assert im.size==(w,h) and x+w<=256 and y+h<=60
        region=occupied[y:y+h,x:x+w]
        assert not np.any(region),name
        region[:]=1
        a=np.array(im)
        assert np.any(a==0) and np.any(a!=0) and a.max()<16,name
        assert not np.any(a[:,0]) and not np.any(a[:,-1]),name
        assert not np.any(a[0]) and not np.any(a[-1]),name
        atlas.paste(im,(x,y))
    a=np.array(atlas,dtype=np.uint8)
    assert np.all(a[60:]==0)
    packed=((a[:,0::2]<<4)|a[:,1::2]).tobytes()
    assert len(packed)==8192 and packed[7680:]==bytes(512)
    unpacked=np.empty_like(a)
    p=np.frombuffer(packed,dtype=np.uint8).reshape(64,128)
    unpacked[:,0::2]=p>>4;unpacked[:,1::2]=p&15
    assert np.array_equal(unpacked,a)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'feature.bin').write_bytes(packed)
    rgba(atlas).save(OUT/'feature-atlas.png')
    rgba(atlas).resize((1024,256),Image.Resampling.NEAREST).save(OUT/'feature-atlas-preview.png')
    header='''/* Generated by tools/generate_feature.py. Original modular art. */
#ifndef NEON_FEATURE_ASSETS_H
#define NEON_FEATURE_ASSETS_H
#include "assets.h"
#define FEATURE_VRAM_BASE 0x7E000UL
#define FEATURE_VRAM_SIZE 8192UL
#define FEATURE_ART_BYTES 7680UL
#define FEATURE_CURSOR_BASE 0x7FE00UL
#define FEATURE_CURSOR_RESERVED_BYTES 512UL
#define FEATURE_HULL_CORE_X 73
#define FEATURE_HULL_CORE_Y 24
#define FEATURE_ARM_LEFT_X (-20)
#define FEATURE_ARM_RIGHT_X 172
'''
    for name in ('hull','arm_left','arm_right'):
        x,y,w,h=PLACEMENT[name]
        header+=f'static const Sprite feature_{name} = {{{x},{y+BASE_Y},{w},{h}}};\n'
    header+='static const Sprite feature_core[2] = {'
    header+=','.join('{%d,%d,%d,%d}'%(x,y+BASE_Y,w,h) for x,y,w,h in
                     (PLACEMENT['core_0'],PLACEMENT['core_1']))
    header+='};\n#endif\n'
    (ROOT/'src/feature_assets.h').write_text(header,encoding='utf-8')
    # Transparent composition previews are art only, not emulator screenshots.
    composite=[]
    for frame in range(16):
        canvas=Image.new('RGBA',(256,128),tuple(PALETTE[1])+(255,))
        x=40+round(math.sin(math.tau*frame/16)*5)
        y=23+round(math.cos(math.tau*frame/16)*2)
        canvas.alpha_composite(rgba(pieces['arm_left']),(x-20,y+((frame%8)<2)*4))
        canvas.alpha_composite(rgba(pieces['arm_right']),(x+172,y+(((frame+4)%8)<2)*4))
        canvas.alpha_composite(rgba(pieces['hull']),(x,y))
        canvas.alpha_composite(rgba(pieces['core_'+str((frame//2)%2)]),(x+73,y+24))
        composite.append(canvas.resize((768,384),Image.Resampling.NEAREST))
    composite[0].save(OUT/'feature-composite.png')
    composite[0].save(OUT/'feature-motion-preview.gif',save_all=True,
                      append_images=composite[1:],duration=90,loop=0,disposal=2)
    manifest=dict(format='V9990 256x64 4bpp; high nibble is even X; transparent index 0',
                  bytes=len(packed),sha256=hashlib.sha256(packed).hexdigest(),
                  vram_base='0x7E000',logical_y=BASE_Y,art_height=60,
                  reserved_cursor_bytes=512,reserved_cursor_range='0x7FE00..0x7FFFF',
                  reserved_cursor_bytes_all_zero=True,palette_rgb5=PALETTE_RGB5,
                  parts={name:dict(x=x,y=BASE_Y+y,w=w,h=h) for name,(x,y,w,h) in PLACEMENT.items()},
                  composition={'hull':[40,23],'arm_left_offset':[-20,0],
                               'arm_right_offset':[172,0],'core_offset':[73,24],
                               'bounding_width':216,'preview_is_emulator_capture':False},
                  verification={'no_atlas_overlap':True,'transparent_margins':True,
                                'nibble_roundtrip':True,'palette_indices_0_to_15':True})
    (OUT/'feature-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    build()
