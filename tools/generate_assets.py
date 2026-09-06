"""Deterministic, original pixel artwork for NEON REVENANT.

No downloaded art or fonts are used.  The binary is V9990 4bpp indexed color,
Sprite VRAM interval 0x10000..0x23fff (logical y=512..1151).
Animated environments are generated separately by generate_world.py.
Even X pixels use the high nibble; odd X pixels use the low nibble.
Run from any directory with Python 3 and Pillow.
"""
from pathlib import Path
import hashlib
import json
import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw
from art_palette import PALETTE_RGB5, PALETTE

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
W, H = 256, 212
BLACK,NAVY,DEEP,SLATE,TEAL,CYAN,ICE,WHITE=PALETTE[:8]
PURPLE,STEEL,VIOLET,PINK,WARM,ORANGE,AMBER,CREAM=PALETTE[8:]
MAGENTA=VIOLET
RED=ORANGE


@lru_cache(maxsize=None)
def palette_index(rgb):
    if rgb == BLACK:
        return 0
    # Color zero is reserved for transparency; all dark opaque art stays nonzero.
    return min(range(1,16), key=lambda i: sum((rgb[c]-PALETTE[i][c])**2 for c in range(3)))


def encoded(rgb):
    r, g, b = rgb[:3]
    return (round(g * 7 / 255) << 5) | (round(r * 7 / 255) << 2) | round(b * 3 / 255)


def decoded(value):
    return (round(((value >> 2) & 7) * 255 / 7),
            round(((value >> 5) & 7) * 255 / 7), round((value & 3) * 255 / 3))


def quantize(im):
    """Quantize source RGB directly to the hardware palette without GRB332."""
    raw=im.tobytes()
    return Image.frombytes("RGB", im.size, bytes(v for i in range(0,len(raw),3) for v in PALETTE[palette_index(tuple(raw[i:i+3]))]))


def line(draw, xy, fill, width=1):
    draw.line(xy, fill=fill, width=width)


def background(stage):
    rng = random.Random(1991 + stage * 101)
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    # Atmospheric bands, stars and horizon haze are deliberately sparse at 256px.
    for y in range(84):
        col = NAVY if y < 46 else (PURPLE if stage != 1 else (0, 36, 85))
        line(d, (0, y, 255, y), col)
    for _ in range(63):
        x, y = rng.randrange(256), rng.randrange(8, 67)
        d.point((x, y), fill=rng.choice([TEAL, (73, 109, 170), (109, 146, 170)]))
    if stage == 0:
        d.ellipse((165, 15, 205, 55), fill=(36, 36, 85))
        d.arc((163, 13, 207, 57), 215, 360, fill=TEAL)
        for y in range(19, 54, 4):
            line(d, (165, y, 205, y), NAVY)
        line(d, (24, 23, 58, 28), TEAL)
        d.point((58, 28), ICE)
    elif stage == 1:
        d.ellipse((28, 18, 58, 48), fill=(109, 36, 0))
        d.ellipse((32, 17, 61, 44), fill=NAVY)
        line(d, (152, 15, 189, 12), (73, 73, 85))
        line(d, (156, 17, 185, 14), TEAL)
    else:
        # A vast orbital ring behind the central machine.
        d.ellipse((62, 12, 194, 71), outline=VIOLET)
        d.arc((66, 15, 190, 68), 185, 350, fill=TEAL)
        d.arc((72, 19, 184, 63), 5, 160, fill=MAGENTA)

    # Far city: varied setbacks, aerials, rooflines, and isolated warm windows.
    for depth in range(2):
        x = -2
        while x < 256:
            bw = rng.randrange(5, 15)
            top = rng.randrange(42, 75) + depth * 5
            col = (36, 0, 85) if depth == 0 else BLACK
            d.rectangle((x, top, x+bw, 89), fill=col)
            if rng.randrange(3) == 0:
                line(d, (x+bw//2, top-5, x+bw//2, top), col)
                d.point((x+bw//2, top-5), fill=PINK)
            for wx in range(x+2, x+bw-1, 3):
                for wy in range(top+4, 84, 5):
                    if rng.random() > .43:
                        d.point((wx, wy), fill=TEAL if depth == 0 else rng.choice([TEAL, (109,73,0)]))
            x += bw+2
    line(d, (0, 85, 255, 85), MAGENTA if stage != 1 else TEAL)
    line(d, (0, 87, 255, 87), VIOLET)

    # Central landmark gives each district a distinct silhouette.
    if stage == 0:
        d.rectangle((110, 53, 115, 84), fill=BLACK)
        d.rectangle((140, 43, 146, 84), fill=BLACK)
        line(d, (141, 44, 141, 78), PINK)
        line(d, (112, 56, 112, 80), TEAL)
        line(d, (139, 50, 147, 50), PINK)
    elif stage == 1:
        for x in [72, 106, 153, 181]:
            d.rectangle((x, 49, x+5, 85), fill=BLACK)
            line(d, (x, 49, x+5, 49), ORANGE)
            for j in range(3):
                line(d, (x+2+j*2, 46-j*4, x+5+j*2, 46-j*4), (36,36,85))
        line(d, (64, 65, 194, 65), TEAL)
        line(d, (64, 67, 194, 67), BLACK)
    else:
        d.polygon([(128, 11), (133, 33), (143, 45), (143, 82), (113,82), (113,45), (123,33)], fill=BLACK)
        d.polygon([(128, 20), (130, 38), (138,47), (138,79), (118,79), (118,47), (126,38)], outline=TEAL)
        line(d, (128, 24, 128, 72), CYAN)
        d.polygon([(128,43), (135,50), (128,59), (121,50)], outline=PINK)
        d.rectangle((110,59,146,62), fill=VIOLET)
        line(d, (110,59,146,59), PINK)

    # Near city walls flare away from the road's fixed perspective.
    for side in [0, 1]:
        def mirror(points):
            return [(255-x if side else x, y) for x,y in points]
        fill = BLACK
        for i, (x, roof, inner, foot) in enumerate([
            (0, 25, 27, 169), (28, 41, 50, 145), (52, 52, 70, 128),
            (73, 62, 87, 111), (91, 72, 102, 98)
        ]):
            x2 = inner
            face = [(x,roof), (x2,roof+8), (x2,foot), (x, min(211, foot+24))]
            d.polygon(mirror(face), fill=fill)
            d.line(mirror([(x2,roof+8),(x2,foot)]), fill=TEAL if (i+stage)%2 else MAGENTA)
            d.line(mirror([(x,roof),(x2,roof+8)]), fill=(36,73,85))
            for wx in range(x+3,x2-2,5):
                for wy in range(roof+15,foot-3,7):
                    if rng.random() > .37:
                        pts = mirror([(wx,wy),(wx+1,wy+1)])
                        d.line(pts,fill=rng.choice([TEAL, TEAL, (73,109,170), ORANGE]))
            # Neon signs have symbols, not text.
            if i < 3:
                sx = x+4
                sign_y = roof+12
                if stage == 1:
                    d.line(mirror([(sx,sign_y),(sx+8,sign_y+2)]),fill=ORANGE,width=2)
                    d.line(mirror([(sx,sign_y+5),(sx+6,sign_y+6)]),fill=ORANGE)
                else:
                    d.line(mirror([(sx,sign_y),(sx+6,sign_y+2),(sx+6,sign_y+14),(sx,sign_y+12),(sx,sign_y)]), fill=PINK if stage == 0 else CYAN)
                    d.line(mirror([(sx+2,sign_y+5),(sx+4,sign_y+6)]),fill=ICE)
        # Overhead structural ribs for the refinery, glowing monoliths for core.
        if stage == 1:
            d.polygon(mirror([(0,9),(7,9),(56,77),(51,83)]),fill=BLACK)
            d.line(mirror([(6,10),(57,79)]),fill=(73,73,0))
            d.line(mirror([(0,91),(62,91)]), fill=(73,36,0),width=3)
            d.line(mirror([(0,93),(61,93)]),fill=ORANGE)
        elif stage == 2:
            d.line(mirror([(9,8),(9,105)]),fill=CYAN)
            d.line(mirror([(12,12),(12,88)]),fill=TEAL)
            d.line(mirror([(18,31),(18,92)]),fill=PINK)

    # Retaining walls and deck. Edges converge on (128,84).
    d.polygon([(0,166),(117,86),(128,84),(16,211),(0,211)],fill=PURPLE)
    d.polygon([(255,166),(139,86),(128,84),(240,211),(255,211)],fill=PURPLE)
    d.polygon([(128,84),(16,211),(240,211)],fill=BLACK)
    # Faint panel strips and regular perspective grid on wet tarmac.
    for x in [40, 72, 100, 156, 184, 216]:
        line(d, (128,85,x,211), NAVY)
    for y in [91,100,113,132,160,199]:
        half=(y-84)*112/127
        line(d,(int(128-half),y,int(128+half),y),NAVY)
    for side in [-1,1]:
        line(d,(128+side*2,85,128+side*112,211),CYAN if stage != 1 else ORANGE)
        line(d,(128+side*5,87,128+side*125,211),TEAL if stage != 1 else (109,73,0))
        for y in [102,115,133,157,190]:
            half=int((y-84)*112/127)
            x=128+side*(half+4)
            d.rectangle((min(x,x+side*3),y,max(x,x+side*3),y+2),fill=ICE if stage != 1 else ORANGE)
        # Asymmetric broken color glints on the asphalt's margins.
        for i in range(24):
            y=rng.randrange(96,211)
            half=int((y-84)*112/127)
            inset=rng.randrange(1,max(2,half//4))
            x=128+side*(half-inset)
            length=max(1,(y-84)//18)
            c=rng.choice([TEAL,NAVY,VIOLET,TEAL]) if stage!=1 else rng.choice([NAVY,(73,36,0),(109,73,0)])
            line(d,(x,y,x-side*length,y),c)
    # Horizon tunnel mouth with runway light studs.
    line(d,(119,87,137,87),CYAN)
    for x in [121,125,131,135]:
        d.point((x,90),fill=PINK)
    return quantize(im)


def bevel_box(d,rect,body=SLATE,light=STEEL,dark=DEEP,cut=2):
    x0,y0,x1,y1=rect
    c=min(cut,max(1,(x1-x0)//3),max(1,(y1-y0)//3))
    d.polygon([(x0+c,y0),(x1-c,y0),(x1,y0+c),(x1,y1-c),
        (x1-c,y1),(x0+c,y1),(x0,y1-c),(x0,y0+c)],fill=dark)
    d.polygon([(x0+c,y0),(x1-c,y0),(x1-1,y0+c),(x0+1,y0+c)],fill=light)
    d.polygon([(x0+1,y0+c),(x1-2,y0+c),(x1-2,y1-2),(x0+c,y1-2)],fill=body)
    line(d,(x0+1,y0+c,x0+1,y1-c),light)


def exhaust(d,x,y,w=5,h=5,warm=False):
    # A recessed emitter with a light-colored hot core, rather than an outline.
    mid,hot,core=(ORANGE,AMBER,CREAM) if warm else (TEAL,CYAN,ICE)
    d.ellipse((x-1,y-1,x+w,y+h),fill=NAVY)
    d.ellipse((x,y,x+w-1,y+h-1),fill=mid)
    if w>=4 and h>=4:
        d.ellipse((x+1,y+1,x+w-2,y+h-2),fill=hot)
    line(d,(x+w//2,y+1,x+w//2,y+h-2),core)


def player_art(pose):
    im=Image.new("RGB",(36,24),BLACK)
    d=ImageDraw.Draw(im)
    # Rear three-quarter pursuit vehicle: substantial armor, side nacelles,
    # an inset canopy, air channels and separate lift surfaces.
    d.polygon([(16,1),(21,3),(24,7),(28,9),(29,11),(34,12),(35,17),
        (29,20),(25,21),(22,19),(19,21),(15,21),(12,19),(9,21),
        (3,19),(0,16),(2,12),(7,11),(10,8),(13,7),(14,3)],fill=NAVY)
    for side in [-1,1]:
        def p(points):
            return [(round(17.5+side*x),y) for x,y in points]
        d.polygon(p([(5,8),(10,9),(12,12),(16,12),(17,16),(11,19),(6,17)]),fill=SLATE)
        d.polygon(p([(7,9),(10,10),(12,13),(15,13),(14,15),(8,15),(5,12)]),fill=STEEL if side<0 else TEAL)
        d.polygon(p([(8,15),(14,15),(12,18),(7,18)]),fill=DEEP)
        d.line(p([(11,12),(15,13)]),fill=ICE if side<0 else STEEL)
        d.line(p([(11,17),(14,16)]),fill=CYAN)
    d.polygon([(15,3),(20,3),(23,8),(24,15),(21,19),(14,19),(11,15),(12,8)],fill=TEAL)
    d.polygon([(14,3),(20,3),(21,7),(19,11),(13,10),(12,8)],fill=STEEL)
    d.polygon([(15,3),(19,3),(20,5),(14,5)],fill=WHITE)
    d.polygon([(15,6),(19,6),(20,8),(18,10),(14,9),(13,8)],fill=DEEP)
    d.polygon([(15,6),(18,6),(19,8),(15,8)],fill=CYAN)
    line(d,(15,6,17,6),ICE)
    d.polygon([(13,11),(18,12),(18,17),(14,17),(12,14)],fill=STEEL)
    d.polygon([(19,11),(22,10),(23,14),(21,17),(19,17)],fill=SLATE)
    line(d,(13,11,15,11),WHITE)
    d.rectangle((16,13,19,16),fill=DEEP)
    line(d,(17,13,18,13),SLATE)
    for x in [3,24]:
        bevel_box(d,(x,10,x+8,22),body=SLATE,light=STEEL,dark=NAVY)
        d.polygon([(x+2,11),(x+6,11),(x+7,14),(x+2,14)],fill=STEEL)
        line(d,(x+2,11,x+5,11),WHITE)
        line(d,(x+1,15,x+7,15),NAVY)
        line(d,(x+2,14,x+3,14),AMBER)
        d.polygon([(x+2,16),(x+6,16),(x+8,18),(x+7,21),(x+5,23),(x+2,22),(x,19)],fill=DEEP)
        exhaust(d,x+1,17,7,6)
        line(d,(x+3,18,x+4,18),WHITE)
        line(d,(x+3,23,x+4,23),CYAN)
    d.rectangle((14,18,21,20),fill=DEEP)
    line(d,(15,18,20,18),STEEL)
    line(d,(16,20,19,20),CYAN)
    if pose!=1:
        # Integer bank transform keeps every material/shadow pixel opaque.
        bank=pose-1
        result=Image.new('RGB',im.size,BLACK)
        for y in range(im.height):
            for x in range(im.width):
                rgb=im.getpixel((x,y))
                if rgb!=BLACK:
                    yy=y+round((x-17.5)*bank*.10)
                    xx=x+round((11-y)*bank*.06)
                    if 0<=xx<36 and 0<=yy<24:
                        result.putpixel((xx,yy),rgb)
        im=result
    return im


def enemy_art(kind):
    im=Image.new("RGB",(54,36),BLACK)
    d=ImageDraw.Draw(im)
    if kind==0:
        # Low, wide interceptor. Split forward intakes and armored shoulder wings.
        d.polygon([(15,5),(22,8),(31,8),(38,5),(47,10),(53,22),
            (48,29),(37,31),(32,28),(21,28),(16,31),(5,29),(0,22),(6,10)],fill=NAVY)
        for side in [-1,1]:
            def p(points): return [(round(26.5+side*x),y) for x,y in points]
            d.polygon(p([(5,10),(12,6),(19,10),(25,21),(19,27),(10,27)]),fill=WARM)
            d.polygon(p([(7,11),(13,8),(18,11),(21,18),(10,18)]),fill=VIOLET)
            d.polygon(p([(12,10),(14,9),(18,12),(18,15),(14,15)]),fill=ORANGE)
            d.line(p([(11,13),(14,17),(19,18)]),fill=WARM)
            d.polygon(p([(10,19),(21,18),(23,23),(17,25),(10,24)]),fill=DEEP)
            d.line(p([(14,10),(17,12)]),fill=CREAM if side<0 else AMBER)
            d.line(p([(12,21),(19,21)]),fill=ORANGE,width=2)
            d.line(p([(13,21),(17,21)]),fill=AMBER)
            d.polygon(p([(9,27),(17,27),(15,31),(10,30)]),fill=WARM)
        d.polygon([(22,5),(31,5),(35,13),(33,27),(27,32),(20,27),(18,13)],fill=SLATE)
        d.polygon([(23,7),(30,7),(32,13),(28,16),(21,13)],fill=STEEL)
        d.polygon([(23,10),(29,10),(30,14),(22,14)],fill=WARM)
        line(d,(24,11,28,11),AMBER)
        d.polygon([(21,17),(27,19),(27,27),(21,25)],fill=TEAL)
        d.polygon([(28,18),(33,16),(31,25),(28,28)],fill=DEEP)
        d.rectangle((24,20,29,24),fill=NAVY)
        line(d,(25,21,28,21),ORANGE)
        line(d,(24,28,29,28),CREAM)
        exhaust(d,8,26,5,5,True)
        exhaust(d,41,26,5,5,True)
    elif kind==1:
        # Gimballed recon drone: a plated spherical core and detached-looking pods.
        d.polygon([(7,11),(18,14),(35,14),(47,11),(51,17),(46,24),
            (35,22),(18,22),(7,24),(2,17)],fill=SLATE)
        for x in [1,42]:
            bevel_box(d,(x,9,x+10,27),body=DEEP,light=STEEL,dark=NAVY)
            d.rectangle((x+3,13,x+7,22),fill=WARM)
            line(d,(x+4,14,x+4,21),ORANGE)
            d.rectangle((x+2,27,x+8,29),fill=SLATE)
        d.ellipse((13,2,40,33),fill=NAVY)
        d.ellipse((14,3,39,30),fill=SLATE)
        d.polygon([(20,4),(32,4),(37,9),(33,13),(20,12),(16,9)],fill=STEEL)
        d.polygon([(15,10),(20,13),(18,23),(15,25)],fill=TEAL)
        d.polygon([(34,12),(39,10),(38,25),(33,28),(31,24)],fill=DEEP)
        d.polygon([(18,25),(23,23),(31,25),(34,29),(28,32),(20,29)],fill=DEEP)
        line(d,(21,5,29,5),WHITE)
        line(d,(17,8,18,7),ICE)
        d.ellipse((18,10,35,27),fill=NAVY)
        d.ellipse((20,12,33,25),fill=WARM)
        d.ellipse((22,14,31,23),fill=ORANGE)
        d.ellipse((24,15,30,20),fill=AMBER)
        d.ellipse((25,16,28,19),fill=CREAM)
        d.point((23,14),WHITE)
        for x in [20,30]:
            line(d,(x,28,x+2,28),STEEL)
        d.rectangle((24,0,29,2),fill=DEEP)
        line(d,(25,0,28,0),ORANGE)
    else:
        # Dense assault sled: ceramic shoulders, recessed heavy weapon barrels.
        d.polygon([(10,4),(18,7),(36,7),(43,4),(50,9),(53,27),
            (44,33),(33,31),(20,31),(9,33),(0,27),(3,9)],fill=NAVY)
        bevel_box(d,(13,4,40,28),body=SLATE,light=STEEL,dark=DEEP,cut=4)
        d.polygon([(18,5),(35,5),(37,10),(32,13),(21,13),(16,10)],fill=TEAL)
        d.polygon([(20,8),(33,8),(32,11),(21,11)],fill=WARM)
        line(d,(22,9,31,9),AMBER)
        for x in [2,37]:
            bevel_box(d,(x,8,x+14,29),body=WARM,light=ORANGE,dark=NAVY,cut=3)
            d.polygon([(x+2,10),(x+11,10),(x+12,16),(x+3,15)],fill=STEEL)
            line(d,(x+3,10,x+9,10),WHITE)
            d.rectangle((x+4,18,x+11,29),fill=DEEP)
            d.rectangle((x+5,21,x+10,30),fill=NAVY)
            line(d,(x+6,27,x+9,27),ORANGE,width=2)
            line(d,(x+7,27,x+8,27),CREAM)
        d.polygon([(18,16),(35,16),(33,25),(28,30),(23,30),(19,25)],fill=SLATE)
        d.polygon([(19,17),(25,18),(25,25),(22,26)],fill=STEEL)
        for y in [19,22,25]:
            line(d,(27,y,32,y),DEEP)
        line(d,(23,29,28,29),AMBER)
    return im


def scaled_enemy(kind,width,height):
    source=enemy_art(kind)
    if width>=18:
        # Area sampling retains solid body mass at middle distances; the mask
        # keeps dark shadows distinct from actual transparent cutouts.
        rgba=source.convert('RGBA')
        rgba.putalpha(Image.frombytes('L',source.size,bytes(0 if p==BLACK else 255
            for p in zip(*[iter(source.tobytes())]*3))))
        scaled=rgba.resize((width,height),Image.Resampling.BOX)
        out=Image.new('RGB',(width,height),BLACK)
        for y in range(height):
            for x in range(width):
                r,g,b,a=scaled.getpixel((x,y))
                if a>=96:
                    out.putpixel((x,y),PALETTE[palette_index((r,g,b))])
        return out
    out=Image.new('RGB',(width,height),BLACK)
    d=ImageDraw.Draw(out)
    c=(width-1)//2
    if kind==0:
        d.polygon([(0,height//2),(2,1),(c,2),(width-3,1),(width-1,height//2),
            (width-2,height-2),(1,height-2)],fill=SLATE)
        line(d,(2,2,width-3,2),STEEL)
        line(d,(1,height-2,width-2,height-2),ORANGE)
        d.point((c,2),CREAM)
    elif kind==1:
        d.ellipse((c-2,0,c+2,height-1),fill=STEEL)
        d.rectangle((0,2,1,height-2),fill=SLATE)
        d.rectangle((width-2,2,width-1,height-2),fill=SLATE)
        d.rectangle((c-1,2,c+1,height-3),fill=ORANGE)
        d.point((c,2),CREAM)
    else:
        d.rectangle((1,1,width-2,height-2),fill=SLATE)
        line(d,(2,1,width-3,1),STEEL)
        d.rectangle((0,2,2,height-1),fill=WARM)
        d.rectangle((width-3,2,width-1,height-1),fill=WARM)
        d.point((1,height-2),AMBER)
        d.point((width-2,height-2),AMBER)
    return out


def explosion_art(phase,size):
    im=Image.new("RGB",(size,size),BLACK)
    d=ImageDraw.Draw(im)
    rng=random.Random(4701+phase*91+size)
    c=(size-1)/2
    def cloud(x,y,r,col):
        d.ellipse((round(x-r),round(y-r),round(x+r),round(y+r)),fill=col)
    if phase==0:
        # A sharp flash with asymmetric particles, never a uniform outlined star.
        cloud(c,c,size*.20,ORANGE)
        cloud(c,c,size*.14,CREAM)
        line(d,(0,round(c),size-1,round(c)),AMBER)
        line(d,(round(c),max(0,int(c-size*.32)),round(c),min(size-1,int(c+size*.32))),WHITE)
        cloud(c,c,max(1,size*.08),WHITE)
    elif phase in [1,2]:
        lobes=[]
        for j in range(9):
            a=j*math.tau/9+.31
            distance=size*(.20 if phase==1 else .28)
            x=c+math.cos(a)*distance
            y=c+math.sin(a)*distance
            r=size*rng.uniform(.13,.20)
            lobes.append((x,y,r))
            cloud(x,y,r,WARM if phase==2 else ORANGE)
        for x,y,r in lobes:
            cloud(x-r*.13,y-r*.17,r*.76,ORANGE if phase==2 else AMBER)
            if phase==1:
                cloud(x-r*.25,y-r*.28,r*.46,CREAM)
        cloud(c,c,size*.24,AMBER if phase==1 else WARM)
        if phase==1:
            cloud(c-size*.04,c-size*.06,size*.18,CREAM)
            cloud(c-size*.06,c-size*.08,size*.1,WHITE)
        else:
            cloud(c+size*.03,c+size*.05,size*.17,PURPLE)
            for j in range(7):
                a=j*math.tau/7
                x=c+math.cos(a)*size*.39;y=c+math.sin(a)*size*.39
                line(d,(round(x),round(y),round(x+math.cos(a)*size*.08),round(y+math.sin(a)*size*.08)),AMBER,max(1,size//24))
    else:
        for j in range(8):
            a=j*math.tau/8+.2
            x=c+math.cos(a)*size*.31;y=c+math.sin(a)*size*.31
            cloud(x,y,size*rng.uniform(.08,.14),PURPLE)
            cloud(x-size*.02,y-size*.02,size*.06,WARM)
            if j%2==0:
                line(d,(round(x),round(y),round(x+math.cos(a)*size*.13),round(y+math.sin(a)*size*.13)),ORANGE,max(1,size//32))
                d.point((round(x),round(y)),AMBER)
    return im


def boss_art(kind):
    im=Image.new("RGB",(96,56),BLACK)
    d=ImageDraw.Draw(im)
    if kind==0:
        # WARDEN: sculpted swept interceptor, four heavy intakes and split armor.
        d.polygon([(15,5),(29,11),(40,8),(48,2),(56,8),(67,11),(80,5),
            (90,14),(95,31),(85,43),(70,46),(60,42),(54,51),(41,51),
            (35,42),(24,46),(10,42),(0,31),(5,15)],fill=NAVY)
        for side in [-1,1]:
            def p(points): return [(48+side*x,y) for x,y in points]
            d.polygon(p([(9,12),(20,15),(32,7),(40,15),(45,30),(34,36),(18,31)]),fill=SLATE)
            d.polygon(p([(14,15),(22,17),(32,10),(38,16),(35,23),(22,26),(13,22)]),fill=STEEL)
            d.polygon(p([(24,28),(38,25),(42,31),(32,38),(24,36)]),fill=DEEP)
            d.line(p([(28,12),(32,11),(37,17)]),fill=WHITE if side<0 else TEAL)
            d.line(p([(19,20),(25,19)]),fill=ICE)
            d.polygon(p([(15,17),(20,18),(23,24),(18,26),(13,22)]),fill=TEAL)
            d.polygon(p([(27,14),(31,12),(35,17),(31,22),(25,24)]),fill=STEEL)
            d.line(p([(27,14),(31,13),(34,17)]),fill=WHITE if side<0 else ICE)
            d.line(p([(22,16),(26,22),(23,28)]),fill=NAVY)
            d.line(p([(30,23),(36,21)]),fill=DEEP)
            d.polygon(p([(35,28),(40,26),(42,30),(37,32)]),fill=SLATE)
            d.line(p([(36,28),(39,27)]),fill=STEEL)
            d.polygon(p([(12,29),(20,27),(26,36),(23,46),(15,46),(11,38)]),fill=WARM)
            d.line(p([(16,31),(21,34),(21,40)]),fill=ORANGE,width=2)
            d.line(p([(17,32),(20,35)]),fill=AMBER)
            for q in [26,31,36]:
                d.line(p([(q,29),(q+2,28)]),fill=NAVY,width=3)
                d.line(p([(q,28),(q+2,27)]),fill=ORANGE)
            d.line(p([(20,39),(22,41)]),fill=AMBER)
            for q in [15,21,32]:
                d.point(p([(q,23)])[0],fill=STEEL)
            x=48+side*30-5
            bevel_box(d,(x,32,x+10,44),body=SLATE,light=STEEL,dark=NAVY)
            exhaust(d,x+2,39,7,5,True)
        d.polygon([(43,4),(52,4),(60,17),(58,35),(51,48),(43,48),(37,35),(35,17)],fill=SLATE)
        d.polygon([(44,6),(51,6),(56,16),(50,20),(40,17)],fill=STEEL)
        d.polygon([(44,10),(50,10),(52,16),(42,16)],fill=DEEP)
        line(d,(44,12,50,12),ORANGE,width=2)
        line(d,(45,12,48,12),CREAM)
        d.polygon([(40,22),(47,25),(47,39),(41,35)],fill=TEAL)
        d.polygon([(49,25),(56,21),(54,35),(49,40)],fill=DEEP)
        for y in [25,29,33]:
            line(d,(42,y,45,y),STEEL)
        line(d,(48,22,48,39),NAVY)
        d.polygon([(41,20),(45,23),(44,27),(39,23)],fill=STEEL)
        d.polygon([(51,21),(56,19),(55,25),(51,27)],fill=SLATE)
        line(d,(41,20,43,21),WHITE)
        line(d,(51,30,53,29),TEAL)
        line(d,(51,34,53,33),TEAL)
        for x,y in [(38,17),(57,17),(41,39),(53,38)]:
            d.point((x,y),STEEL)
        d.rectangle((43,41,51,46),fill=NAVY)
        line(d,(44,43,50,43),ORANGE)
        line(d,(46,44,48,44),CREAM)
    elif kind==1:
        # RAZOR: broad siege chassis with offset layered plates and dual cannons.
        d.polygon([(16,3),(29,8),(65,8),(79,3),(90,14),(95,42),
            (86,51),(65,51),(56,47),(39,47),(30,51),(8,49),(0,40),(5,14)],fill=NAVY)
        bevel_box(d,(24,5,71,43),body=SLATE,light=STEEL,dark=DEEP,cut=6)
        d.polygon([(31,7),(63,7),(68,15),(61,22),(34,22),(27,15)],fill=TEAL)
        d.polygon([(33,10),(61,10),(63,16),(59,18),(36,18),(30,15)],fill=NAVY)
        d.polygon([(34,11),(60,11),(60,14),(35,14)],fill=WARM)
        line(d,(36,12,57,12),ORANGE)
        line(d,(37,12,45,12),CREAM)
        for x in [4,69]:
            bevel_box(d,(x,12,x+22,46),body=WARM,light=ORANGE,dark=NAVY,cut=5)
            d.polygon([(x+4,13),(x+17,13),(x+20,21),(x+16,25),(x+3,23)],fill=STEEL)
            line(d,(x+5,14,x+14,14),WHITE)
            d.polygon([(x+5,16),(x+10,16),(x+13,22),(x+6,21)],fill=TEAL)
            d.polygon([(x+12,16),(x+16,16),(x+18,20),(x+15,23)],fill=SLATE)
            line(d,(x+11,15,x+14,23),NAVY)
            line(d,(x+6,18,x+8,18),ICE)
            d.rectangle((x+5,25,x+17,43),fill=DEEP)
            for y in [27,31,35]:
                line(d,(x+7,y,x+15,y),SLATE)
            bevel_box(d,(x+7,36,x+17,52),body=SLATE,light=TEAL,dark=NAVY)
            for y in [38,42]:
                line(d,(x+8,y,x+15,y),DEEP)
                line(d,(x+9,y+1,x+11,y+1),STEEL)
            exhaust(d,x+9,46,6,5,True)
            line(d,(x+2,29,x+2,36),AMBER)
            for yy in [28,33,38]:
                d.point((x+20,yy),STEEL)
        for x in [27,63]:
            d.rectangle((x,23,x+5,39),fill=NAVY)
            for yy in [24,28,32,36]:
                line(d,(x+1,yy,x+4,yy),TEAL)
                d.point((x+1,yy),STEEL)
        d.polygon([(42,22),(53,22),(62,29),(64,40),(56,49),(41,51),(32,42),(31,31)],fill=NAVY)
        d.polygon([(42,24),(52,24),(60,30),(61,39),(54,47),(42,48),(34,41),(33,32)],fill=SLATE)
        d.polygon([(42,24),(52,24),(60,30),(56,32),(40,30),(34,35),(33,32)],fill=STEEL)
        line(d,(42,24,50,24),WHITE)
        d.polygon([(42,28),(52,28),(57,33),(57,41),(51,45),(42,45),(37,40),(37,34)],fill=DEEP)
        for j in range(8):
            a=j*math.tau/8
            x=48+math.cos(a)*10;y=37+math.sin(a)*9
            line(d,(round(x),round(y),round(x+math.cos(a)*2),round(y+math.sin(a)*2)),SLATE,width=2)
        d.ellipse((40,29,55,44),fill=WARM)
        d.ellipse((43,31,53,41),fill=ORANGE)
        d.ellipse((45,32,51,37),fill=AMBER)
        line(d,(46,33,49,33),CREAM)
        d.rectangle((43,2,52,5),fill=DEEP)
        line(d,(44,2,50,2),ORANGE)
        line(d,(30,19,34,22),SLATE)
        line(d,(61,20,65,17),SLATE)
        for x in [34,60]:
            d.point((x,8),WHITE)
    else:
        # NOX: ceramic/mauve command shell; a luminous buried reactor and wings.
        d.polygon([(45,1),(52,1),(63,9),(76,6),(88,15),(95,31),
            (87,41),(73,39),(62,49),(52,54),(41,54),(31,48),(22,40),
            (8,41),(0,31),(7,15),(20,7),(33,10)],fill=NAVY)
        for side in [-1,1]:
            def p(points): return [(48+side*x,y) for x,y in points]
            d.polygon(p([(12,14),(26,8),(35,15),(43,29),(35,35),(23,31),(15,36)]),fill=SLATE)
            d.polygon(p([(18,15),(26,11),(32,16),(35,23),(26,25),(16,23)]),fill=STEEL)
            d.polygon(p([(28,28),(39,28),(40,33),(31,35),(24,32)]),fill=DEEP)
            d.line(p([(25,13),(30,15)]),fill=ICE)
            d.polygon(p([(18,17),(23,15),(26,21),(22,24),(16,22)]),fill=TEAL)
            d.polygon(p([(27,13),(31,16),(34,22),(30,23),(26,18)]),fill=STEEL)
            d.line(p([(24,14),(27,21),(24,27)]),fill=NAVY)
            d.line(p([(29,15),(32,18)]),fill=WHITE if side<0 else ICE)
            d.line(p([(31,26),(37,26)]),fill=NAVY,width=3)
            for q in [31,34,37]:
                d.line(p([(q,26),(q,28)]),fill=STEEL)
            d.line(p([(20,19),(28,20)]),fill=VIOLET,width=2)
            d.line(p([(22,19),(27,20)]),fill=PINK)
            d.polygon(p([(12,32),(20,33),(25,43),(20,48),(13,43)]),fill=STEEL)
            d.polygon(p([(14,35),(18,36),(20,43),(17,42)]),fill=VIOLET)
            d.line(p([(16,37),(18,42)]),fill=PINK)
            d.line(p([(14,36),(17,35),(20,40)]),fill=NAVY)
            d.line(p([(14,35),(16,35)]),fill=ICE)
            d.polygon(p([(30,18),(33,19),(36,24),(33,24)]),fill=DEEP)
        d.polygon([(42,3),(53,3),(62,14),(65,30),(58,45),(49,52),(39,47),(31,30),(34,14)],fill=SLATE)
        d.polygon([(42,5),(52,5),(59,15),(55,20),(39,19),(36,14)],fill=STEEL)
        d.polygon([(42,6),(46,6),(46,14),(41,17),(38,13)],fill=TEAL)
        d.polygon([(48,6),(51,6),(56,14),(52,16),(48,14)],fill=SLATE)
        line(d,(47,5,47,16),NAVY)
        line(d,(40,10,41,8),ICE)
        d.polygon([(35,19),(41,22),(38,33),(43,45),(36,40),(32,29)],fill=TEAL)
        d.polygon([(57,19),(63,17),(63,29),(57,42),(53,45),(57,32)],fill=DEEP)
        d.polygon([(42,17),(53,17),(58,27),(53,40),(47,46),(40,37),(36,27)],fill=NAVY)
        d.polygon([(43,20),(51,20),(54,28),(49,39),(45,39),(40,28)],fill=VIOLET)
        d.polygon([(45,23),(50,24),(51,29),(47,37),(43,28)],fill=PINK)
        d.polygon([(46,25),(49,26),(49,30),(47,33),(45,28)],fill=CREAM)
        line(d,(43,8,49,8),WHITE)
        line(d,(43,46,49,49),STEEL)
        for x in [38,54]:
            line(d,(x,15,x+3,16),DEEP)
        for y in [24,29,34]:
            line(d,(34,y,36,y+1),STEEL)
            line(d,(59,y,61,y-1),TEAL)
        line(d,(41,43,45,46),DEEP)
        line(d,(51,46,54,42),DEEP)
    return im


# Compact, authored 5x7 bitmap alphabet. Each row is a five-bit string.
GLYPHS = {
    'A':[14,17,17,31,17,17,17], 'B':[30,17,17,30,17,17,30],
    'C':[15,16,16,16,16,16,15], 'D':[30,17,17,17,17,17,30],
    'E':[31,16,16,30,16,16,31], 'F':[31,16,16,30,16,16,16],
    'G':[15,16,16,23,17,17,15], 'H':[17,17,17,31,17,17,17],
    'I':[31,4,4,4,4,4,31], 'J':[7,2,2,2,18,18,12],
    'K':[17,18,20,24,20,18,17], 'L':[16,16,16,16,16,16,31],
    'M':[17,27,21,21,17,17,17], 'N':[17,25,21,19,17,17,17],
    'O':[14,17,17,17,17,17,14], 'P':[30,17,17,30,16,16,16],
    'Q':[14,17,17,17,21,18,13], 'R':[30,17,17,30,20,18,17],
    'S':[15,16,16,14,1,1,30], 'T':[31,4,4,4,4,4,4],
    'U':[17,17,17,17,17,17,14], 'V':[17,17,17,17,17,10,4],
    'W':[17,17,17,21,21,21,10], 'X':[17,17,10,4,10,17,17],
    'Y':[17,17,10,4,4,4,4], 'Z':[31,1,2,4,8,16,31],
    '0':[14,17,19,21,25,17,14], '1':[4,12,4,4,4,4,14],
    '2':[14,17,1,2,4,8,31], '3':[30,1,1,14,1,1,30],
    '4':[2,6,10,18,31,2,2], '5':[31,16,16,30,1,1,30],
    '6':[14,16,16,30,17,17,14], '7':[31,1,2,4,8,8,8],
    '8':[14,17,17,14,17,17,14], '9':[14,17,17,15,1,1,14],
    ' ':[0]*7, '!':[4,4,4,4,4,0,4], '?':[14,17,1,2,4,0,4],
    '-':[0,0,0,31,0,0,0], '+':[0,4,4,31,4,4,0],
    '.':[0,0,0,0,0,12,12], ',':[0,0,0,0,0,4,8],
    ':':[0,4,4,0,4,4,0], ';':[0,4,4,0,4,4,8],
    '/':[1,2,2,4,8,8,16], '\\':[16,8,8,4,2,2,1],
    '(':[2,4,8,8,8,4,2], ')':[8,4,2,2,2,4,8],
    '[':[14,8,8,8,8,8,14], ']':[14,2,2,2,2,2,14],
    '<':[0,2,4,8,4,2,0], '>':[0,8,4,2,4,8,0],
    '=':[0,0,31,0,31,0,0], '_':[0,0,0,0,0,0,31],
    '*':[0,17,10,31,10,17,0], '"':[10,10,10,0,0,0,0],
    "'":[4,4,4,0,0,0,0], '#':[10,31,10,10,31,10,0],
    '%':[17,2,4,4,8,16,17], '&':[12,18,20,8,21,18,13],
    '@':[14,17,23,21,23,16,15], '^':[4,10,17,0,0,0,0],
    '|':[4,4,4,4,4,4,4], '~':[0,0,9,22,0,0,0],
    '$':[4,15,20,14,5,30,4], '`':[8,4,2,0,0,0,0],
    '{':[2,4,4,8,4,4,2], '}':[8,4,4,2,4,4,8],
}


def glyph(ch):
    im=Image.new("RGB",(6,8),BLACK)
    px=im.load()
    for y,row in enumerate(GLYPHS.get(ch.upper(),GLYPHS['?'])):
        for x in range(5):
            if row & (1<<(4-x)):
                px[x,y]=WHITE
    return im


def title_art():
    """A restrained chrome wordmark with custom cut-corner letterforms."""
    # Opaque midnight isolates the chrome lettering from detailed moving scenery.
    im=Image.new('RGB',(232,50),NAVY)
    plate=ImageDraw.Draw(im)
    line(plate,(0,0,11,0),TEAL)
    line(plate,(220,0,231,0),SLATE)
    line(plate,(0,49,11,49),SLATE)
    line(plate,(220,49,231,49),SLATE)
    mask=Image.new('1',(232,50))
    md=ImageDraw.Draw(mask)
    shapes={
        'E':[[(0,0),(20,0),(20,4),(5,4),(5,9),(16,9),(16,13),(5,13),(5,18),(20,18),(20,22),(0,22)]],
        'N':[[(0,22),(0,0),(5,0),(15,14),(15,0),(20,0),(20,22),(15,22),(5,8),(5,22)]],
        'V':[[(0,0),(5,0),(10,16),(15,0),(20,0),(13,22),(7,22)]],
        'A':[[(0,22),(6,0),(14,0),(20,22),(15,22),(13,15),(7,15),(5,22)]],
        'T':[[(0,0),(20,0),(20,5),(13,5),(13,22),(7,22),(7,5),(0,5)]],
        'R':[[(0,22),(0,0),(15,0),(20,4),(20,10),(15,14),(21,22),(15,22),(9,14),(5,14),(5,22)]],
    }
    for n,ch in enumerate('REVENANT'):
        def xy(poly): return [(15+n*25+x+(22-y)//8,17+y) for x,y in poly]
        for polygon in shapes[ch]:
            md.polygon(xy(polygon),fill=1)
        if ch=='A':
            md.polygon(xy([(9,5),(11,5),(12,10),(8,10)]),fill=0)
        elif ch=='R':
            md.polygon(xy([(5,4),(13,4),(15,6),(15,9),(13,10),(5,10)]),fill=0)
    mp=mask.load();px=im.load()
    for y in range(17,40):
        for x in range(230):
            if mp[x,y]:
                px[x+1,y+1]=DEEP
    for y in range(17,40):
        color=WHITE if y<23 else ICE if y<27 else STEEL if y<30 else WHITE if y==30 else TEAL
        for x in range(232):
            if mp[x,y]:
                px[x,y]=color
    # Quiet identity line above the stronger primary title.
    for n,ch in enumerate('NEON'):
        for row,bits in enumerate(GLYPHS[ch]):
            for col in range(5):
                if bits & (1<<(4-col)):
                    for xx in [0,1]:
                        for yy in [0,1]:
                            px[84+n*17+col*2+xx,1+row*2+yy]=ICE
    d=ImageDraw.Draw(im)
    line(d,(16,8,68,8),SLATE)
    line(d,(166,8,217,8),SLATE)
    line(d,(16,8,32,8),CYAN)
    line(d,(203,8,217,8),CYAN)
    draw_bitmap_text(im,'NIGHT OPERATIONS',68,43,STEEL)
    return im


def draw_bitmap_text(im,text,x,y,color=ICE):
    pixels=im.load()
    for ch in text:
        for gy,row in enumerate(GLYPHS.get(ch.upper(),GLYPHS['?'])):
            for gx in range(5):
                if row & (1<<(4-gx)) and 0<=x+gx<im.width and 0<=y+gy<im.height:
                    pixels[x+gx,y+gy]=color
        x+=6


def hud_art(top):
    im=Image.new('RGB',(256,18 if top else 14),NAVY)
    d=ImageDraw.Draw(im)
    if top:
        d.rectangle((0,0,255,2),fill=DEEP)
        line(d,(0,17,255,17),SLATE)
        line(d,(0,17,32,17),CYAN)
        for x in [81,169]: line(d,(x,5,x,12),SLATE)
    else:
        line(d,(0,0,255,0),SLATE)
        line(d,(0,0,32,0),CYAN)
        for x in [70,137,224]: line(d,(x,4,x,10),DEEP)
    labels=[('SCORE',5,5),('HI',88,5),('SECTOR',174,5),('/3',230,5)] if top else [
        ('SH',5,4),('BOMB',76,4),('SPD',143,4),('KM/H',190,4)]
    for text,x,y in labels:
        draw_bitmap_text(im,text,x,y,STEEL if text!='/3' else TEAL)
    return quantize(im)


def banner_art(title,subtitle):
    im=Image.new('RGB',(216,24),NAVY)
    d=ImageDraw.Draw(im)
    warning=subtitle.startswith('WARNING')
    line(d,(0,0,215,0),SLATE)
    line(d,(0,23,215,23),DEEP)
    d.rectangle((0,0,2,23),fill=ORANGE if warning else CYAN)
    line(d,(213,0,215,0),ORANGE if warning else CYAN)
    draw_bitmap_text(im,title,(216-len(title)*6)//2,4,WHITE)
    draw_bitmap_text(im,subtitle,(216-len(subtitle)*6)//2,14,AMBER if warning else STEEL)
    return quantize(im)


class Atlas:
    def __init__(self):
        self.image=Image.new("RGB",(256,640),BLACK)
        self.x,self.y,self.rowh=0,512,0
        self.records={}
    def put(self,name,im):
        w,h=im.size
        if self.x+w>256:
            self.x=0; self.y+=self.rowh+1; self.rowh=0
        if self.y+h>1152:
            raise ValueError("Sprite atlas overlaps animated-world storage")
        value=(self.x,self.y,w,h)
        self.records[name]=value
        self.image.paste(im,(self.x,self.y-512))
        self.x+=w+1; self.rowh=max(self.rowh,h)
        return value


def c_sprite(v): return "{%d,%d,%d,%d}"%tuple(v)


def sprite_gallery():
    """Native-size evidence beside integral enlargements of the same pixels."""
    gallery=Image.new('RGB',(840,580),NAVY)
    def put(sprite,x,y,scale=1):
        if scale!=1:
            sprite=sprite.resize((sprite.width*scale,sprite.height*scale),Image.Resampling.NEAREST)
        mask=Image.frombytes('L',sprite.size,bytes(0 if p==BLACK else 255
            for p in zip(*[iter(sprite.tobytes())]*3)))
        gallery.paste(sprite,(x,y),mask)
    draw_bitmap_text(gallery,'NEON REVENANT / MSX3 MATERIAL STUDY',18,14,WHITE)
    draw_bitmap_text(gallery,'ORIGINAL PIXELS + NEAREST-NEIGHBOR DETAIL',18,30,STEEL)
    for i in range(3):
        x=20+i*280
        draw_bitmap_text(gallery,['BANK LEFT','PURSUIT VEHICLE','BANK RIGHT'][i],x,48,ICE)
        put(player_art(i),x,62,4)
        put(player_art(i),x+190,86)
        draw_bitmap_text(gallery,['INTERCEPTOR','GIMBAL DRONE','ASSAULT SLED'][i],x,190,AMBER)
        put(enemy_art(i),x,210,3)
        put(enemy_art(i),x+184,236)
        draw_bitmap_text(gallery,['WARDEN','RAZOR','NOX'][i],x,354,ICE)
        put(boss_art(i),x,374,2)
        put(boss_art(i),x+48,508)
    return gallery


def main():
    ASSETS.mkdir(exist_ok=True)
    (ROOT/'src').mkdir(exist_ok=True)
    atlas=Atlas()
    players=[atlas.put(f'player_{i}',player_art(i)) for i in range(3)]
    enemies=[]
    for kind in range(3):
        enemies.append([atlas.put(f'enemy_{kind}_{w}',scaled_enemy(kind,w,max(6,round(w*2/3)))) for w in [8,12,18,26,38,54]])
    explosions=[[atlas.put(f'explosion_{phase}_{size}',explosion_art(phase,size)) for size in [8,16,24,40,56]] for phase in range(4)]
    bosses=[atlas.put(f'boss_{kind}',boss_art(kind)) for kind in range(3)]
    bulletim=Image.new('RGB',(5,10),BLACK); d=ImageDraw.Draw(bulletim)
    d.ellipse((0,1,4,8),fill=WARM); d.ellipse((1,0,3,8),fill=ORANGE); line(d,(2,1,2,6),CREAM)
    bullet=atlas.put('bullet',bulletim)
    pickupim=Image.new('RGB',(13,13),BLACK); d=ImageDraw.Draw(pickupim)
    d.polygon([(4,0),(8,0),(12,4),(12,8),(8,12),(4,12),(0,8),(0,4)],fill=NAVY)
    d.polygon([(4,1),(8,1),(11,4),(11,8),(8,11),(4,11),(1,8),(1,4)],fill=SLATE)
    line(d,(3,2,8,2),STEEL); line(d,(1,4,1,7),TEAL)
    d.rectangle((5,3,7,9),fill=CYAN); d.rectangle((3,5,9,7),fill=CYAN)
    line(d,(5,4,5,7),ICE)
    pickup=atlas.put('pickup',pickupim)
    reticleim=Image.new('RGB',(21,21),BLACK); d=ImageDraw.Draw(reticleim)
    for coords in [(0,5,0,0,5,0),(15,0,20,0,20,5),(0,15,0,20,5,20),(15,20,20,20,20,15)]:
        line(d,coords,NAVY,width=3)
        line(d,coords,ICE)
    for x,y in [(4,10),(16,10),(10,4),(10,16)]: d.point((x,y),STEEL)
    line(d,(9,10,11,10),CYAN); d.point((10,9),CYAN); d.point((10,11),CYAN)
    reticle=atlas.put('reticle',reticleim)
    font=[atlas.put(f'font_{i}',glyph(chr(i))) for i in range(32,128)]
    titlelogo=atlas.put('titleLogo',title_art())
    hud_top=atlas.put('hud_top',hud_art(True))
    hud_bottom=atlas.put('hud_bottom',hud_art(False))
    stagebanners=[atlas.put(f'stage_banner_{i}',banner_art(title,'BREAK THROUGH THE NIGHT'))
        for i,title in enumerate(['01 CHROME DISTRICT','02 SKYWAY ASSAULT','03 THE BLACK SPIRE'])]
    bossbanners=[atlas.put(f'boss_banner_{i}',banner_art(title,'WARNING - HEAVY CONTACT'))
        for i,title in enumerate(['WARDEN / INTERCEPTOR','RAZOR / SIEGE CARRIER','NOX / CENTRAL CORE'])]
    header=['/* Generated by tools/generate_assets.py. Original deterministic artwork. */',
        '#ifndef NEON_ASSETS_H','#define NEON_ASSETS_H',
        'typedef struct { unsigned char x; unsigned int y; unsigned char w,h; } Sprite;',
        '#define ASSETS_VRAM_BASE 0x10000UL', '#define ASSETS_VRAM_SIZE 81920UL',
        'static const Sprite player[3] = {'+','.join(map(c_sprite,players))+'};',
        'static const Sprite enemy[3][6] = {\n'+',\n'.join(' {'+','.join(map(c_sprite,row))+'}' for row in enemies)+'\n};',
        'static const Sprite explosion[4][5] = {\n'+',\n'.join(' {'+','.join(map(c_sprite,row))+'}' for row in explosions)+'\n};',
        'static const Sprite bosses[3] = {'+','.join(map(c_sprite,bosses))+'};',
        'static const Sprite bullet = '+c_sprite(bullet)+';',
        'static const Sprite pickup = '+c_sprite(pickup)+';',
        'static const Sprite reticle = '+c_sprite(reticle)+';',
        'static const Sprite titleLogo = '+c_sprite(titlelogo)+';',
        '#define HUD_TOP_Y '+str(hud_top[1]),
        '#define HUD_BOTTOM_Y '+str(hud_bottom[1]),
        'static const Sprite stageBanner[3] = {'+','.join(map(c_sprite,stagebanners))+'};',
        'static const Sprite bossBanner[3] = {'+','.join(map(c_sprite,bossbanners))+'};',
        '/* ASCII 32..127. Each glyph is 6x8, with transparent background. */',
        'static const Sprite font[96] = {\n'+',\n'.join(' '+','.join(map(c_sprite,font[i:i+8])) for i in range(0,96,8))+'\n};',
        '#endif','']
    (ROOT/'src'/'assets.h').write_text('\n'.join(header),encoding='ascii')
    colormap=[palette_index(decoded(v)) for v in range(256)]
    paletteheader=['/* Generated RGB5 palette and legacy GGGRRRBB color translation. */',
        '#ifndef NEON_PALETTE_H','#define NEON_PALETTE_H',
        'static const unsigned char v9990_palette[48] = {\n'+
        ',\n'.join(' '+','.join(map(str,rgb)) for rgb in PALETTE_RGB5)+'\n};',
        'static const unsigned char color_map[256] = {\n'+
        ',\n'.join(' '+','.join(map(str,colormap[i:i+16])) for i in range(0,256,16))+'\n};',
        '#endif','']
    (ROOT/'src'/'palette.h').write_text('\n'.join(paletteheader),encoding='ascii')
    raw=atlas.image.tobytes()
    indices=bytes(palette_index(tuple(raw[i:i+3])) for i in range(0,len(raw),3))
    data=bytes((indices[i]<<4)|indices[i+1] for i in range(0,len(indices),2))
    assert len(data)==81920
    (ASSETS/'vram.bin').write_bytes(data)
    quantize(atlas.image).save(ASSETS/'atlas.png')
    # Show sprites at real pixel size and enlarged without interpolation.
    gallery=sprite_gallery()
    gallery.save(ASSETS/'sprite-material-preview.png')
    gallery.save(ASSETS/'preview.png')
    title_art().resize((928,200),Image.Resampling.NEAREST).save(ASSETS/'title-logo.png')
    title_art().save(ASSETS/'title-logo-native.png')
    scaleview=Image.new('RGB',(420,190),NAVY)
    for kind in range(3):
        x=8
        for width in [8,12,18,26,38,54]:
            spriteim=scaled_enemy(kind,width,max(6,round(width*2/3)))
            scaleview.paste(spriteim,(x,kind*60+14))
            x+=width+10
    scaleview.resize((840,380),Image.Resampling.NEAREST).save(ASSETS/'enemy-scale-preview.png')
    effects=Image.new('RGB',(360,270),NAVY)
    for phase in range(4):
        x=12
        for size in [8,16,24,40,56]:
            effects.paste(explosion_art(phase,size),(x,phase*64+8))
            x+=size+15
    effects.paste(bulletim,(268,26))
    effects.paste(pickupim,(292,24))
    effects.paste(reticleim,(319,20))
    effects.resize((720,540),Image.Resampling.NEAREST).save(ASSETS/'effects-preview.png')
    ui=Image.new('RGB',(256,210),NAVY)
    ui.paste(hud_art(True),(0,0))
    ui.paste(hud_art(False),(0,24))
    for i,record in enumerate(stagebanners+bossbanners):
        x,y,w,h=record
        ui.paste(atlas.image.crop((x,y-512,x+w,y-512+h)),(20,46+i*27))
    quantize(ui).resize((768,630),Image.Resampling.NEAREST).save(ASSETS/'ui-preview.png')
    manifest={'format':'V9990 4bpp indexed RGB5','base':65536,'bytes':len(data),
        'packing':'even X high nibble; odd X low nibble',
        'palette_rgb5':PALETTE_RGB5,'palette_rgb8':PALETTE,
        'sha256':hashlib.sha256(data).hexdigest(),'last_atlas_y':atlas.y+atlas.rowh,
        'backgrounds':[],
        'sprites':atlas.records}
    (ASSETS/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:manifest[k] for k in ['format','base','bytes','sha256','last_atlas_y']},indent=2))


if __name__=='__main__':
    main()
