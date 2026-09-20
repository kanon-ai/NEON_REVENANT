"""Dedicated static SCREEN2 title, using all three independent PCG banks."""
import numpy as np
from PIL import Image,ImageDraw
from pcg_art import _two_colors,PALETTE
from pcg_codec import _encode

def build_title(assets,out,background=None):
    frame=(np.load(assets/'frames-1.npy')[0] if background is None else background).copy()
    frame[:16]=1;frame[176:]=1
    im=Image.fromarray(frame);d=ImageDraw.Draw(im)
    font=(assets/'source/font.bin').read_bytes()
    def text(s,x,y,scale=1,color=15,slant=False):
        for i,c in enumerate(s):
            for row,b in enumerate(font[(ord(c)-32)*8:(ord(c)-31)*8]):
                for col in range(8):
                    if b&(128>>col):
                        px=x+i*8*scale+col*scale+(7-row if slant else 0)
                        py=y+row*scale
                        fill=color if isinstance(color,int) else color[min(len(color)-1,row)]
                        d.rectangle((px,py,px+scale-1,py+scale-1),fill=fill)
    d.rectangle((12,20,243,91),fill=1)
    d.line((20,23,85,23),fill=7);d.line((171,23,235,23),fill=7)
    text('NEON',96,20,2,7)
    text('REVENANT',31,47,3,4,True)
    text('REVENANT',28,44,3,[15,15,14,7,7,4,4,5],True)
    text('NIGHT OPERATIONS',64,76,1,14)
    d.rectangle((31,107,224,136),fill=1)
    text('MIDNIGHT INTERCEPTION',48,110,1,7)
    text('PRESS FIRE TO LAUNCH',52,126,1,15)
    d.rectangle((24,148,231,175),fill=1)
    text('ARROWS / JOYSTICK : MOVE',36,153,1,14)
    text('FIRE : SHOT    X : NOVA',40,164,1,14)
    text('MSX / PSG',4,2,1,7);text('512K ROM',188,2,1,7)
    text('ORIGINAL CODE / ART / MUSIC',24,181,1,14)
    frame=_two_colors(np.asarray(im))
    v=bytearray(16384)
    for band in range(3):
        cache={}
        for ty in range(band*8,band*8+8):
            for tx in range(32):
                tile=_encode(frame[ty*8:ty*8+8,tx*8:tx*8+8])
                if tile not in cache:
                    idx=len(cache);cache[tile]=idx
                    a=band*2048+idx*8;v[a:a+8]=tile[:8];v[8192+a:8200+a]=tile[8:]
                v[0x3800+ty*32+tx]=cache[tile]
        assert len(cache)<=256
    v[0x3C00:0x3F00]=v[0x3800:0x3B00]
    v[0x3B00]=v[0x3B80]=208
    (assets/'title.bin').write_bytes(v)
    Image.fromarray(np.array(PALETTE,dtype=np.uint8)[frame]).resize((768,576),Image.Resampling.NEAREST).save(out/'title-reference.png')
